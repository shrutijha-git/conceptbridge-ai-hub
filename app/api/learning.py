import json
import io
import csv
import httpx

from pathlib import Path
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
)

from sqlalchemy import select, text 
from sqlalchemy.orm import Session

from pypdf import PdfReader

from app.db.database import get_db
from app.core.config import get_settings
from app.api.routes import require_session
from app.api.auth import get_current_user

from app.ai.context_builder import get_memory
from app.rag.retrieval import split_chunks
from app.learning.practice import (
    QUESTIONS,
    public_question,
    assess,
    analyze_sales,
)

from app.models.entities import (
    User,
    Document,
    DocumentChunk,
    SessionDocument,
    PracticeAttempt,
    Mistake,
    VideoSegment,
    VideoBookmark,
    DataAnalysis,
    utcnow,
)

from app.schemas.chat import (
    AttemptRequest,
    VideoCreate,
    VideoBookmarkCreate,
)


router = APIRouter()


# ============================================================
# DOCUMENTS
# ============================================================


@router.post("/documents", status_code=201)
def upload_document(
    session_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = require_session(
        db,
        session_id,
        current_user,
    )

    name = Path(file.filename or "notes.txt").name[:255]
    suffix = Path(name).suffix.lower()

    if suffix not in {".pdf", ".txt", ".md"}:
        raise HTTPException(
            422,
            "Use a text-based PDF, TXT or Markdown file.",
        )

    data = file.file.read(5_000_001)

    if not data or len(data) > 5_000_000:
        raise HTTPException(
            413,
            "Use a non-empty file up to 5 MB.",
        )

    try:
        if suffix == ".pdf":
            pdf = PdfReader(io.BytesIO(data))

            if pdf.is_encrypted:
                raise ValueError(
                    "Use an unencrypted PDF."
                )

            if len(pdf.pages) > 30:
                raise ValueError(
                    "Use up to 30 PDF pages."
                )

            pages = [
                (i + 1, p.extract_text() or "")
                for i, p in enumerate(pdf.pages)
            ]

        else:
            pages = [
                (None, data.decode("utf-8-sig"))
            ]

        size = sum(
            len(text)
            for _, text in pages
        )

        if size < 30:
            raise ValueError(
                "Not enough readable text. Scanned PDFs need OCR first."
            )

        if size > 60000:
            raise ValueError(
                "Use a shorter chapter, up to 60,000 extracted characters."
            )

    except Exception as exc:
        msg = (
            str(exc)
            if isinstance(exc, ValueError)
            else
            "The document could not be read. "
            "Try a text-based PDF or UTF-8 text."
        )

        raise HTTPException(
            422,
            msg,
        ) from None

    doc_id = str(uuid4())

    root = get_settings().storage_dir.resolve()

    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    key = f"{doc_id}{suffix}"
    path = root / key

    try:
        path.write_bytes(data)

        doc = Document(
            id=doc_id,
            user_id=session.user_id,
            filename=name,
            storage_key=key,
            embedding_status="lexical_ready",
        )

        db.add(doc)
        db.flush()

        db.add(
            SessionDocument(
                session_id=session.id,
                document_id=doc.id,
            )
        )

        chunks = split_chunks(pages)

        for i, (page, text) in enumerate(chunks):
            db.add(
                DocumentChunk(
                    document_id=doc.id,
                    chunk_no=i,
                    page_number=page,
                    text=text,
                )
            )

        db.commit()

    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise

    return {
        "document_id": doc_id,
        "filename": name,
        "chunks": len(chunks),
        "retrieval": "lexical",
        "embeddings_created": False,
    }


@router.get("/sessions/{session_id}/documents")
def documents(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = require_session(
        db,
        session_id,
        current_user,
    )

    rows = db.scalars(
        select(Document)
        .join(
            SessionDocument,
            SessionDocument.document_id == Document.id,
        )
        .where(
            SessionDocument.session_id == session.id,
            Document.user_id == session.user_id,
        )
    ).all()

    return [
        {
            "document_id": document.id,
            "filename": document.filename,
            "retrieval_status": document.embedding_status,
        }
        for document in rows
    ]



@router.delete("/sessions/{session_id}/documents/{document_id}")
def delete_document(
    session_id: UUID,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a document from the authenticated user's learning session.

    The session-document link is always removed.

    If no other session references the document:
        1. Delete document chunks
        2. Delete the document
        3. Delete the stored physical file
    """

    # --------------------------------------------------------
    # 1. Verify that the session belongs to the logged-in user
    # --------------------------------------------------------

    session = require_session(
        db,
        session_id,
        current_user,
    )

    # --------------------------------------------------------
    # 2. Find the document linked to this session
    # --------------------------------------------------------

    document = db.scalar(
        select(Document)
        .join(
            SessionDocument,
            SessionDocument.document_id == Document.id,
        )
        .where(
            SessionDocument.session_id == session.id,
            SessionDocument.document_id == document_id,
            Document.user_id == str(current_user.id),
        )
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found in this learning session.",
        )

    # Save this BEFORE deleting the database row.
    storage_key = document.storage_key

    try:
        # ----------------------------------------------------
        # 3. Remove the session-document relationship
        # ----------------------------------------------------

        db.execute(
            text(
                """
                DELETE FROM session_documents
                WHERE session_id = :session_id
                  AND document_id = :document_id
                """
            ),
            {
                "session_id": str(session.id),
                "document_id": str(document.id),
            },
        )

        # ----------------------------------------------------
        # 4. Check whether another session still uses
        #    this document
        # ----------------------------------------------------

        remaining_link = db.execute(
            text(
                """
                SELECT 1
                FROM session_documents
                WHERE document_id = :document_id
                LIMIT 1
                """
            ),
            {
                "document_id": str(document.id),
            },
        ).first()

        # ----------------------------------------------------
        # 5. If no other session uses the document,
        #    completely delete it.
        # ----------------------------------------------------

        if remaining_link is None:

            # IMPORTANT:
            # document_chunks MUST be deleted FIRST.
            #
            # MySQL foreign key:
            #
            # document_chunks.document_id
            #       ↓
            # documents.id
            #
            # Therefore the child rows must disappear before
            # the parent document row.

            db.execute(
                text(
                    """
                    DELETE FROM document_chunks
                    WHERE document_id = :document_id
                    """
                ),
                {
                    "document_id": str(document.id),
                },
            )

            # ------------------------------------------------
            # 6. Now delete the parent document
            # ------------------------------------------------

            db.execute(
                text(
                    """
                    DELETE FROM documents
                    WHERE id = :document_id
                    """
                ),
                {
                    "document_id": str(document.id),
                },
            )

        # ----------------------------------------------------
        # 7. Commit database changes
        # ----------------------------------------------------

        db.commit()

    except Exception as exc:
        db.rollback()

        print(
            "\n========== DOCUMENT DELETE ERROR =========="
        )
        print(type(exc).__name__)
        print(str(exc))
        print(
            "===========================================\n"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not delete the document. "
                "Check the backend terminal."
            ),
        ) from None

    # --------------------------------------------------------
    # 8. Delete physical file ONLY after successful DB commit
    # --------------------------------------------------------

    if remaining_link is None and storage_key:

        storage_path = (
            get_settings().storage_dir.resolve()
            / storage_key
        )

        try:
            storage_path.unlink(
                missing_ok=True
            )
        except OSError as exc:
            print(
                "Warning: database deletion succeeded, "
                f"but physical file could not be removed: {exc}"
            )

    return {
        "deleted": True,
        "document_id": document_id,
    }


# ============================================================
# PRACTICE
# ============================================================


@router.get("/practice/questions")
def questions(
    mode: str | None = None,
):
    if mode is not None and mode not in {
        "understand",
        "practise",
        "code",
    }:
        raise HTTPException(
            422,
            "Unknown learning mode",
        )

    return [
        public_question(question_id)
        for question_id, question in QUESTIONS.items()
        if mode is None or question["mode"] == mode
    ]


@router.post("/practice/attempts", status_code=201)
def practice_attempt(
    payload: AttemptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = require_session(
        db,
        payload.session_id,
        current_user,
        lock=True,
    )

    if not payload.answer.strip():
        raise HTTPException(
            422,
            "Make an attempt first.",
        )

    try:
        feedback = assess(
            payload.question_id,
            payload.answer,
        )

    except ValueError as exc:
        raise HTTPException(
            422,
            str(exc),
        ) from None

    question = QUESTIONS[payload.question_id]

    attempt = PracticeAttempt(
        session_id=session.id,
        concept=question["concept"],
        mode=question["mode"],
        question_id=payload.question_id,
        answer=payload.answer,
        feedback_json=json.dumps(feedback),
    )

    db.add(attempt)

    if feedback["verdict"] == "needs-practice":

        db.add(
            Mistake(
                session_id=session.id,
                concept=question["concept"],
                mistake_type=feedback["method"],
                explanation=feedback["explanation"],
            )
        )

        memory = get_memory(
            db,
            session,
        )

        state = json.loads(
            memory.state_json
        )

        state["weak_concepts"] = list(
            dict.fromkeys(
                [
                    *state.get("weak_concepts", []),
                    question["concept"],
                ]
            )
        )[-15:]

        memory.state_json = json.dumps(state)

    elif feedback["correct"] is True:

        memory = get_memory(
            db,
            session,
        )

        state = json.loads(
            memory.state_json
        )

        state["weak_concepts"] = [
            concept
            for concept in state.get("weak_concepts", [])
            if concept != question["concept"]
        ]

        memory.state_json = json.dumps(state)

    db.commit()

    return {
        "attempt_id": attempt.id,
        "concept": question["concept"],
        "feedback": feedback,
    }


@router.get("/sessions/{session_id}/progress")
def progress(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = require_session(
        db,
        session_id,
        current_user,
    )

    rows = db.scalars(
        select(PracticeAttempt)
        .where(
            PracticeAttempt.session_id == session.id
        )
        .order_by(
            PracticeAttempt.created_at.desc(),
            PracticeAttempt.id,
        )
        .limit(200)
    ).all()

    concepts = {}

    for row in rows:

        feedback = json.loads(
            row.feedback_json
        )

        if row.concept not in concepts:
            concepts[row.concept] = {
                "concept": row.concept,
                "latest_status": feedback["verdict"],
                "follow_up": feedback["follow_up"],
                "attempts": 0,
            }

        concepts[row.concept]["attempts"] += 1

    return {
        "attempts": len(rows),
        "concepts": list(concepts.values()),
        "scope": "latest 200 attempts",
        "mastery_calibrated": False,
    }


# ============================================================
# DATA PRACTICE
# ============================================================


@router.post("/practice/data")
def data_practice(
    file: UploadFile = File(...),
    date_column: str = Form(
        "date",
        min_length=1,
        max_length=255,
    ),
    value_column: str = Form(
        "sales",
        min_length=1,
        max_length=255,
    ),
    category_column: str = Form(
        "region",
        min_length=1,
        max_length=255,
    ),
    grouping: str = Form(...),
    aggregation: str = Form(...),
    chart: str = Form(...),
    session_id: UUID | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(
        lambda: None
    ),
):
    """
    Data analysis can still be used without a session.

    If a session_id is supplied, the frontend must use the
    authenticated session through the session-specific routes.
    """

    session = None

    if session_id is not None:

        # Resolve authentication explicitly for session-backed
        # Data Lab requests.
        from app.api.auth import get_current_user as _get_current_user

        raise HTTPException(
            status_code=401,
            detail=(
                "Session-backed Data Lab requests require authentication. "
                "Use the authenticated Data Lab request flow."
            ),
        )

    if (
        grouping not in {
            "month",
            "region",
            "row",
        }
        or aggregation not in {
            "sum",
            "average",
            "count",
        }
        or chart not in {
            "line",
            "bar",
            "pie",
        }
    ):
        raise HTTPException(
            422,
            "Choose a supported grouping, aggregation and chart.",
        )

    raw = file.file.read(
        2_000_001
    )

    if len(raw) > 2_000_000:
        raise HTTPException(
            413,
            "Use a CSV up to 2 MB.",
        )

    try:
        result = analyze_sales(
            raw.decode("utf-8-sig"),
            date_column,
            value_column,
            category_column,
        )

    except (
        ValueError,
        UnicodeDecodeError,
        csv.Error,
    ) as exc:
        raise HTTPException(
            422,
            str(exc),
        ) from None

    issues = []

    if grouping != "month":
        issues.append(
            "For a monthly trend, group by month."
        )

    if aggregation != "sum":
        issues.append(
            "For total sales, use SUM."
        )

    if chart not in {
        "line",
        "bar",
    }:
        issues.append(
            "Use a line or bar chart to keep months in order."
        )

    response = {
        "task": "Show the monthly sales trend",
        "feedback": {
            "verdict": (
                "needs-practice"
                if issues
                else "on-track"
            ),
            "issues": issues,
        },
        "calculated_reference": result,
    }

    return response


def serialize_analysis(
    row: DataAnalysis,
):
    return {
        **row.result_json,
        "analysis_id": row.id,
        "session_id": row.session_id,
        "filename": row.filename,
        "choices": row.choices_json,
        "created_at": row.created_at.isoformat() + "Z",
    }


@router.get("/sessions/{session_id}/data-analyses")
def data_analyses(
    session_id: UUID,
    limit: int = Query(
        20,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = require_session(
        db,
        session_id,
        current_user,
    )

    rows = db.scalars(
        select(DataAnalysis)
        .where(
            DataAnalysis.session_id == session.id
        )
        .order_by(
            DataAnalysis.created_at.desc(),
            DataAnalysis.id.desc(),
        )
        .limit(limit)
    ).all()

    return [
        serialize_analysis(row)
        for row in rows
    ]


# ============================================================
# VIDEO SEGMENTS
# ============================================================


@router.post(
    "/videos/segments",
    status_code=201,
)
def add_video(
    payload: VideoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = require_session(
        db,
        payload.session_id,
        current_user,
    )

    values = payload.model_dump(
        exclude={"session_id"}
    )

    row = VideoSegment(
        session_id=session.id,
        **values,
        verification="user_supplied",
    )

    db.add(row)
    db.commit()

    return serialize_video(row)


def serialize_video(row):
    return {
        "id": row.id,
        "video_id": row.video_id,
        "title": row.title,
        "topic": row.topic,
        "start_seconds": row.start_seconds,
        "end_seconds": row.end_seconds,
        "evidence": row.evidence,
        "verification": row.verification,
        "watch_url": (
            f"https://www.youtube.com/watch?v={row.video_id}"
            f"&t={row.start_seconds}s"
        ),
        "embed_url": (
            f"https://www.youtube.com/embed/{row.video_id}"
            f"?start={row.start_seconds}"
            f"&end={row.end_seconds}"
        ),
        "note": (
            "Times and topic relevance were supplied by the curator; "
            "not independently verified by ConceptBridge. "
            "The watch link starts at the timestamp; "
            "the embed includes an end boundary."
        ),
    }


@router.get(
    "/sessions/{session_id}/videos"
)
def get_videos(
    session_id: UUID,
    topic: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = require_session(
        db,
        session_id,
        current_user,
    )

    rows = db.scalars(
        select(VideoSegment)
        .where(
            VideoSegment.session_id == session.id
        )
        .limit(100)
    ).all()

    return [
        serialize_video(row)
        for row in rows
        if (
            not topic
            or topic.casefold()
            in row.topic.casefold()
        )
    ]


# ============================================================
# VIDEO BOOKMARKS
# ============================================================


def serialize_video_bookmark(
    row: VideoBookmark,
):
    return {
        "id": row.id,
        "video_id": row.video_id,
        "timestamp_seconds": row.timestamp_seconds,
        "note": row.note,
        "created_at": row.created_at,
        "watch_url": (
            f"https://www.youtube.com/watch?v={row.video_id}"
            f"&t={row.timestamp_seconds}s"
        ),
    }


@router.post(
    "/videos/bookmarks",
    status_code=201,
)
def add_video_bookmark(
    payload: VideoBookmarkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = require_session(
        db,
        payload.session_id,
        current_user,
    )

    row = VideoBookmark(
        session_id=session.id,
        video_id=payload.video_id,
        timestamp_seconds=payload.timestamp_seconds,
        note=payload.note.strip(),
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    return serialize_video_bookmark(row)


@router.get(
    "/sessions/{session_id}/video-bookmarks"
)
def get_video_bookmarks(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = require_session(
        db,
        session_id,
        current_user,
    )

    rows = db.scalars(
        select(VideoBookmark)
        .where(
            VideoBookmark.session_id == session.id
        )
        .order_by(
            VideoBookmark.created_at.desc()
        )
        .limit(200)
    ).all()

    return [
        serialize_video_bookmark(row)
        for row in rows
    ]


# ============================================================
# YOUTUBE SEARCH
# ============================================================


@router.get("/youtube/search")
async def search_youtube(
    q: str = Query(
        ...,
        min_length=2,
        max_length=100,
    ),
    max_results: int = Query(
        8,
        ge=1,
        le=25,
    ),
):
    settings = get_settings()

    if not settings.youtube_api_key:
        raise HTTPException(
            status_code=500,
            detail="YouTube API key is not configured.",
        )

    params = {
        "part": "snippet",
        "q": q,
        "type": "video",
        "maxResults": max_results,
        "key": settings.youtube_api_key,
        "safeSearch": "moderate",
    }

    try:

        async with httpx.AsyncClient(
            timeout=15
        ) as client:

            response = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params,
            )

        if response.status_code != 200:

            try:
                error_data = response.json()
            except Exception:
                error_data = {}

            message = (
                error_data
                .get("error", {})
                .get(
                    "message",
                    "YouTube API request failed.",
                )
            )

            raise HTTPException(
                status_code=response.status_code,
                detail=message,
            )

        data = response.json()

        results = []

        for item in data.get(
            "items",
            [],
        ):

            video_id = (
                item.get(
                    "id",
                    {},
                )
                .get("videoId")
            )

            snippet = item.get(
                "snippet",
                {},
            )

            if not video_id:
                continue

            results.append(
                {
                    "video_id": video_id,
                    "title": snippet.get(
                        "title",
                        "",
                    ),
                    "description": snippet.get(
                        "description",
                        "",
                    ),
                    "channel_title": snippet.get(
                        "channelTitle",
                        "",
                    ),
                    "published_at": snippet.get(
                        "publishedAt"
                    ),
                    "thumbnail": (
                        snippet.get(
                            "thumbnails",
                            {},
                        )
                        .get(
                            "high",
                            {},
                        )
                        .get("url")
                        or
                        snippet.get(
                            "thumbnails",
                            {},
                        )
                        .get(
                            "medium",
                            {},
                        )
                        .get("url")
                        or
                        snippet.get(
                            "thumbnails",
                            {},
                        )
                        .get(
                            "default",
                            {},
                        )
                        .get("url")
                    ),
                    "youtube_url": (
                        f"https://www.youtube.com/watch?v={video_id}"
                    ),
                }
            )

        return {
            "query": q,
            "results": results,
        }

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=(
                "YouTube search timed out. "
                "Please try again."
            ),
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"YouTube search failed: {str(exc)}",
        )
    