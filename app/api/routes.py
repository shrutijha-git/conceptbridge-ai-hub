import hashlib
import json
import re
from uuid import uuid4, UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.ai.prompt_enhancer import enhance_tutor_prompt
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.api.auth import get_current_user

from app.ai.context_builder import (
    build_context,
    get_memory,
    compact_memory,
    ordered_history,
)

from app.ai.router import (
    generate_with_routing,
    RoutingError,
    provider_candidates,
)

from app.ai.providers.base import ProviderError

from app.core.config import get_settings
from app.db.database import get_db

from app.models.entities import (
    Course,
    LearningSession,
    Message,
    User,
    ChatTurn,
    ProviderCall,
)

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    DemoSessionRequest,
    DemoSessionResponse,
    MemoryPatch,
)


router = APIRouter()


# ============================================================
# SESSION CREATE SCHEMA
# ============================================================

class SessionCreate(BaseModel):
    degree: str = Field(
        min_length=1,
        max_length=50,
    )

    subject: str = Field(
        min_length=1,
        max_length=150,
    )

    topic: str = Field(
        min_length=1,
        max_length=255,
    )


# ============================================================
# SESSION OWNERSHIP
# ============================================================

def require_session(
    db: Session,
    session_id,
    current_user: User,
    lock: bool = False,
):
    """
    Return a learning session only if it belongs to the
    currently authenticated user.

    This prevents one user from accessing another user's
    sessions by knowing or guessing a session ID.
    """

    query = select(LearningSession).where(
        LearningSession.id == str(session_id),
        LearningSession.user_id == str(current_user.id),
    )

    if lock:
        query = query.with_for_update(nowait=True)

    try:
        session = db.scalar(query)

    except OperationalError as exc:
        if (
            not getattr(exc.orig, "args", [])
            or exc.orig.args[0] not in {3572, 1205, 1213}
        ):
            raise

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail={
                "code": "session_busy",
                "message": (
                    "This session is busy. "
                    "Retry the same request_id after "
                    "the current turn completes."
                ),
            },
        ) from None

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Learning session not found",
        )

    return session


# ============================================================
# HEALTH / READINESS
# ============================================================

@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ConceptBridge API",
        "mode": "local_development",
    }


@router.get("/ready")
def ready(
    db: Session = Depends(get_db),
):
    try:
        db.execute(text("SELECT 1"))

    except Exception:
        raise HTTPException(
            status_code=503,
            detail=(
                "MySQL is not ready. "
                "Check the local database and .env."
            ),
        ) from None

    return {
        "status": "ready",
        "database": "mysql",
    }


# ============================================================
# AI PROVIDERS
# ============================================================

@router.get("/providers")
def providers():
    settings = get_settings()

    return {
        "default_provider": settings.default_provider,
        "auto_order": settings.provider_order,
        "mock_enabled": (
            settings.enable_mock
            and settings.app_env == "development"
        ),
        "configuration_only": True,
        "providers": [
            {
                "id": provider,
                "configured": bool(
                    getattr(
                        settings,
                        provider + "_api_key",
                    )
                ),
                "model": getattr(
                    settings,
                    provider + "_model",
                ),
            }
            for provider in [
                "gemini",
                "openai",
                "anthropic",
            ]
        ],
    }


# ============================================================
# DEMO SESSION
# ============================================================

@router.post(
    "/demo/session",
    response_model=DemoSessionResponse,
    status_code=201,
)
def create_demo_session(
    payload: DemoSessionRequest,
    db: Session = Depends(get_db),
):
    """
    Legacy development-only demo session.

    This remains available for local development and does
    not replace authenticated user sessions.
    """

    user = User(
        name="Demo Student",
        email=f"demo-{uuid4()}@conceptbridge.local",
    )

    db.add(user)
    db.flush()

    course = Course(
        user_id=user.id,
        degree=payload.degree,
        subject=payload.subject,
    )

    db.add(course)
    db.flush()

    session = LearningSession(
        user_id=user.id,
        course_id=course.id,
        current_topic=payload.topic,
        current_provider="none",
    )

    db.add(session)
    db.flush()

    get_memory(
        db,
        session,
    )

    db.commit()

    return DemoSessionResponse(
        session_id=session.id,
        user_id=user.id,
        course_id=course.id,
    )


# ============================================================
# AUTHENTICATED USER SESSIONS
# ============================================================

@router.get("/sessions")
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return only learning sessions belonging to the
    authenticated user.

    Course information is included because degree and
    subject are stored on Course, while topic/provider
    are stored on LearningSession.
    """

    rows = db.execute(
        select(
            LearningSession,
            Course,
        )
        .join(
            Course,
            Course.id == LearningSession.course_id,
        )
        .where(
            LearningSession.user_id
            == str(current_user.id)
        )
        .order_by(
            LearningSession.updated_at.desc(),
            LearningSession.id,
        )
        .limit(100)
    ).all()

    return [
        {
            "session_id": session.id,
            "degree": course.degree,
            "subject": course.subject,
            "topic": session.current_topic,
            "provider": session.current_provider,
            "updated_at": session.updated_at,
        }
        for session, course in rows
    ]


# ============================================================
# CREATE AUTHENTICATED USER SESSION
# ============================================================

@router.post(
    "/sessions",
    status_code=201,
)
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a learning session for the authenticated user.

    Course stores:
        degree
        subject

    LearningSession stores:
        topic
        provider
    """

    degree = payload.degree.strip()
    subject = payload.subject.strip()
    topic = payload.topic.strip()

    if not degree:
        raise HTTPException(
            status_code=422,
            detail="Degree is required.",
        )

    if not subject:
        raise HTTPException(
            status_code=422,
            detail="Subject is required.",
        )

    if not topic:
        raise HTTPException(
            status_code=422,
            detail="Topic is required.",
        )

    # --------------------------------------------------------
    # Create course for authenticated user
    # --------------------------------------------------------

    course = Course(
        user_id=str(current_user.id),
        degree=degree,
        subject=subject,
    )

    db.add(course)
    db.flush()

    # --------------------------------------------------------
    # Create learning session
    # --------------------------------------------------------

    session = LearningSession(
        user_id=str(current_user.id),
        course_id=course.id,
        current_topic=topic,
        current_provider="none",
    )

    db.add(session)
    db.flush()

    # --------------------------------------------------------
    # Initialize learning memory
    # --------------------------------------------------------

    get_memory(
        db,
        session,
    )

    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "degree": degree,
        "subject": subject,
        "topic": topic,
        "provider": session.current_provider,
        "updated_at": session.updated_at,
    }


# ============================================================
# SESSION MEMORY
# ============================================================

@router.get(
    "/sessions/{session_id}/memory"
)
def read_memory(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = require_session(
        db,
        session_id,
        current_user,
    )

    memory = get_memory(
        db,
        session,
    )

    return {
        "session_id": session.id,
        "topic": session.current_topic,
        "current_provider": session.current_provider,
        "learning_state": json.loads(
            memory.state_json
        ),
        "recap": session.summary,
        "recap_type": "extractive",
        "completed_turns": memory.next_turn - 1,
    }


@router.patch(
    "/sessions/{session_id}/memory"
)
def update_memory(
    session_id: UUID,
    payload: MemoryPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = require_session(
        db,
        session_id,
        current_user,
        lock=True,
    )

    memory = get_memory(
        db,
        session,
    )

    state = json.loads(
        memory.state_json
    )

    state.update(
        payload.model_dump(
            exclude_unset=True
        )
    )

    memory.state_json = json.dumps(
        state,
        ensure_ascii=False,
    )

    db.commit()

    return {
        "session_id": session.id,
        "learning_state": state,
    }


# ============================================================
# CHAT / AI TUTOR
# ============================================================

@router.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Process an AI learning turn only for a session owned
    by the authenticated user.

    The Prompt Enhancer prepares a richer tutor prompt using:
    - degree
    - subject
    - current topic
    - learning memory
    - uploaded study context
    - recent conversation

    The enhancer does NOT call an AI model.
    The existing provider router still handles the actual AI call.
    """

    # --------------------------------------------------------
    # 1. Verify session ownership
    # --------------------------------------------------------

    session = require_session(
        db,
        payload.session_id,
        current_user,
        lock=True,
    )

    # --------------------------------------------------------
    # 2. Request ID + idempotency fingerprint
    # --------------------------------------------------------

    request_id = str(
        payload.request_id or uuid4()
    )

    fingerprint = hashlib.sha256(
        json.dumps(
            payload.model_dump(
                mode="json",
                exclude={"request_id"},
            ),
            sort_keys=True,
        ).encode()
    ).hexdigest()

    # --------------------------------------------------------
    # 3. Check whether this request was already completed
    # --------------------------------------------------------

    prior = db.scalar(
        select(ChatTurn).where(
            ChatTurn.request_id == request_id
        )
    )

    if prior:
        if (
            prior.session_id != session.id
            or prior.request_hash != fingerprint
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "This request_id was already used "
                    "with different input."
                ),
            )

        return json.loads(
            prior.response_json
        )

    # --------------------------------------------------------
    # 4. Load learning memory
    # --------------------------------------------------------

    memory = get_memory(
        db,
        session,
    )

    # --------------------------------------------------------
    # 5. Build the existing ConceptBridge context
    #
    #    This remains unchanged so your existing RAG,
    #    memory and conversation behavior continues working.
    # --------------------------------------------------------

    try:
        system, messages, context = build_context(
            db,
            session,
            payload.message,
            payload.mode,
        )

        # ----------------------------------------------------
        # 6. Load course information
        #
        #    Degree + subject are stored on Course.
        # ----------------------------------------------------

        course = db.get(
            Course,
            session.course_id,
        )

        degree = (
            getattr(course, "degree", None)
            if course
            else None
        )

        subject = (
            getattr(course, "subject", None)
            if course
            else None
        )

        # ----------------------------------------------------
        # 7. Read learning preferences from memory
        #
        #    We support the common keys without breaking your
        #    existing memory structure.
        # ----------------------------------------------------

        try:
            learning_state = json.loads(
                memory.state_json
            )
        except (TypeError, ValueError):
            learning_state = {}

        if not isinstance(learning_state, dict):
            learning_state = {}

        learning_goal = (
            learning_state.get("learning_goal")
            or learning_state.get("goal")
            or learning_state.get("learningGoal")
        )

        explanation_style = (
            learning_state.get("explanation_style")
            or learning_state.get(
                "preferred_explanation_style"
            )
            or learning_state.get("explanationStyle")
        )

        # ----------------------------------------------------
        # 8. Prepare uploaded/RAG context for Prompt Enhancer
        #
        #    build_context already contains the context used
        #    by your existing Tutor. We convert it safely to
        #    text without changing its structure.
        # ----------------------------------------------------

        if context:
            if isinstance(context, str):
                notes_context = context
            else:
                notes_context = json.dumps(
                    context,
                    ensure_ascii=False,
                    indent=2,
                )

            # Remove internal document/chunk UUIDs from the
            # context sent to the AI. These are backend
            # identifiers and should never appear in the
            # student's answer.
            notes_context = re.sub(
                r"\s*\[[0-9a-fA-F]{8}-"
                r"[0-9a-fA-F]{4}-"
                r"[0-9a-fA-F]{4}-"
                r"[0-9a-fA-F]{4}-"
                r"[0-9a-fA-F]{12}\]",
                "",
                notes_context,
            )
        else:
            notes_context = None

        # ----------------------------------------------------
        # 9. Prepare recent conversation
        #
        #    build_context already provides the conversation
        #    messages, so we reuse them instead of querying
        #    the database again.
        # ----------------------------------------------------

        recent_messages = []

        if isinstance(messages, list):
            for message in messages[-8:]:
                if isinstance(message, dict):
                    recent_messages.append(message)
                else:
                    recent_messages.append(
                        {
                            "role": getattr(
                                message,
                                "role",
                                "user",
                            ),
                            "content": getattr(
                                message,
                                "content",
                                str(message),
                            ),
                        }
                    )

        # ----------------------------------------------------
        # 10. Enhance the Tutor prompt
        #
        #     IMPORTANT:
        #     This function does NOT call OpenAI/Gemini/Claude.
        #     It only prepares the instruction.
        # ----------------------------------------------------

        enhanced_system = enhance_tutor_prompt(
            payload.message,
            degree=degree,
            subject=subject,
            topic=session.current_topic,
            learning_goal=learning_goal,
            explanation_style=explanation_style,
            notes_context=notes_context,
            recent_messages=recent_messages,
        )

        # ----------------------------------------------------
        # 11. Preserve the original ConceptBridge Tutor
        #     system instructions/context as well.
        # ----------------------------------------------------

        final_system = (
            enhanced_system
            + "\n\n"
            + "EXISTING CONCEPTBRIDGE TUTOR INSTRUCTIONS:\n"
            + str(system)
        )

        # ----------------------------------------------------
        # 12. Send enhanced prompt through existing AI router
        # ----------------------------------------------------

        routed = generate_with_routing(
            payload.provider,
            final_system,
            messages,
            payload.allow_fallback,
        )

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from None

    except ProviderError as exc:
        db.rollback()

        status = (
            503
            if exc.retryable
            or exc.code == "not_configured"
            else 502
        )

        raise HTTPException(
            status_code=status,
            detail={
                "code": exc.code,
                "message": str(exc),
                "request_id": request_id,
                "route_events": getattr(
                    exc,
                    "route_events",
                    [],
                ),
                "transcript_saved": False,
            },
        ) from None

    # --------------------------------------------------------
    # 13. AI response
    # --------------------------------------------------------

    result = routed.result

    clean_response = re.sub(
        r"\s*\[[0-9a-fA-F]{8}-"
        r"[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{12}\]",
        "",
        result.text,
    ).strip()

    previous = (
        session.current_provider
        if session.current_provider != "none"
        else None
    )

    # --------------------------------------------------------
    # 14. Save user message
    # --------------------------------------------------------

    user_message = Message(
        session_id=session.id,
        role="user",
        content=payload.message,
    )

    # --------------------------------------------------------
    # 15. Save assistant response
    # --------------------------------------------------------

    assistant = Message(
        session_id=session.id,
        role="assistant",
        content=clean_response,
        provider=result.provider,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )

    db.add_all(
        [
            user_message,
            assistant,
        ]
    )

    db.flush()

    # --------------------------------------------------------
    # 16. Build API response
    # --------------------------------------------------------

    response = ChatResponse(
        session_id=session.id,
        request_id=request_id,
        provider_requested=payload.provider,
        provider_used=result.provider,
        previous_provider=previous,
        provider_changed=(
            previous is not None
            and previous != result.provider
        ),
        fallback_used=routed.fallback_used,
        is_mock=result.provider == "mock",
        response=clean_response,
        turn_no=memory.next_turn,
        route_events=routed.route_events,
        usage={
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "estimated_cost": (
                0
                if result.provider == "mock"
                else None
            ),
        },
        context=context,
    )

    # --------------------------------------------------------
    # 17. Save ChatTurn for idempotency/history
    # --------------------------------------------------------

    turn = ChatTurn(
        request_id=request_id,
        request_hash=fingerprint,
        session_id=session.id,
        turn_no=memory.next_turn,
        user_message_id=user_message.id,
        assistant_message_id=assistant.id,
        response_json=response.model_dump_json(),
    )

    db.add(turn)
    db.flush()

    # --------------------------------------------------------
    # 18. Save provider usage
    # --------------------------------------------------------

    db.add(
        ProviderCall(
            session_id=session.id,
            turn_id=turn.id,
            provider=result.provider,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            estimated_cost=(
                0
                if result.provider == "mock"
                else None
            ),
            route_events_json=json.dumps(
                routed.route_events
            ),
        )
    )

    # --------------------------------------------------------
    # 19. Update learning session state
    # --------------------------------------------------------

    session.current_provider = result.provider

    memory.next_turn += 1

    compact_memory(
        db,
        session,
        memory,
    )

    # --------------------------------------------------------
    # 20. Commit everything together
    # --------------------------------------------------------

    db.commit()

    return response


# ============================================================
# SESSION MESSAGES
# ============================================================

@router.get(
    "/sessions/{session_id}/messages"
)
def get_messages(
    session_id: UUID,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_session(
        db,
        session_id,
        current_user,
    )

    if not 2 <= limit <= 1000:
        raise HTTPException(
            status_code=422,
            detail="limit must be 2 to 1000",
        )

    rows = ordered_history(
        db,
        str(session_id),
        limit,
    )

    return [
        {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "provider": message.provider,
            "sequence_in_page": index + 1,
        }
        for index, message in enumerate(rows)
    ]


# ============================================================
# SESSION USAGE
# ============================================================

@router.get(
    "/sessions/{session_id}/usage"
)
def get_usage(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_session(
        db,
        session_id,
        current_user,
    )

    rows = db.scalars(
        select(ProviderCall)
        .where(
            ProviderCall.session_id
            == str(session_id)
        )
        .order_by(
            ProviderCall.created_at
        )
        .limit(500)
    ).all()

    return {
        "calls": [
            {
                "provider": row.provider,
                "model": row.model,
                "input_tokens": row.input_tokens,
                "output_tokens": row.output_tokens,
                "estimated_cost": row.estimated_cost,
                "route_events": json.loads(
                    row.route_events_json
                ),
            }
            for row in rows
        ],
        "note": (
            "Usage is provider-reported for completed "
            "responses. Unknown monetary cost is null. "
            "Failed/timed-out provider work may still "
            "incur charges."
        ),
    }