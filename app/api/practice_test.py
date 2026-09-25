import json
import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from pydantic import BaseModel, Field

from app.ai.router import (
    generate_with_routing,
    RoutingError,
)

from app.ai.providers.base import ProviderError

from app.api.auth import get_current_user
from app.models.entities import User


router = APIRouter()


# ============================================================
# IN-MEMORY PRACTICE TEST STORAGE
# ============================================================

PRACTICE_TESTS = {}


# ============================================================
# REQUEST SCHEMAS
# ============================================================


class PracticeTestGenerateRequest(BaseModel):

    degree: str = Field(
        min_length=1,
        max_length=150,
    )

    subject: str = Field(
        min_length=1,
        max_length=150,
    )

    topic: str = Field(
        min_length=1,
        max_length=255,
    )

    difficulty: str = Field(
        default="Medium",
        min_length=1,
        max_length=30,
    )


class PracticeTestSubmitRequest(BaseModel):

    test_id: str = Field(
        min_length=1
    )

    answers: dict[str, str]


# ============================================================
# PROMPT
# ============================================================


def build_batch_prompt(
    degree: str,
    subject: str,
    topic: str,
    difficulty: str,
    start_number: int,
    end_number: int,
) -> str:

    count = end_number - start_number + 1

    return f"""
Generate exactly {count} multiple-choice questions for:

Degree: {degree}
Subject: {subject}
Topic: {topic}
Difficulty: {difficulty}

Generate questions numbered {start_number} through {end_number}.

Rules:

- Exactly {count} questions.
- Exactly 4 options per question.
- Exactly one correct answer.
- Questions must be directly related to the topic.
- Match the academic level of the degree.
- Avoid duplicate questions.
- Keep questions and options concise.
- Do not include explanations.
- Return ONLY valid JSON.
- Do not use Markdown.
- Do not add any text outside JSON.

Use this exact structure:

{{
  "questions": [
    {{
      "id": "q{start_number}",
      "question": "Question text",
      "options": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "correct_answer": "Option A"
    }}
  ]
}}

The IDs must continue sequentially from q{start_number}
through q{end_number}.
"""


# ============================================================
# PARSE AI RESPONSE
# ============================================================


def parse_batch_response(
    content: str,
    expected_start: int,
    expected_count: int,
):

    content = content.strip()

    if content.startswith("```"):

        lines = content.splitlines()

        if (
            lines
            and lines[0].strip().startswith("```")
        ):
            lines = lines[1:]

        if (
            lines
            and lines[-1].strip() == "```"
        ):
            lines = lines[:-1]

        content = "\n".join(lines).strip()

    try:
        data = json.loads(content)

    except json.JSONDecodeError:

        raise HTTPException(
            status_code=502,
            detail=(
                "The AI returned invalid JSON "
                "while generating the test."
            ),
        ) from None

    questions = data.get("questions")

    if not isinstance(
        questions,
        list,
    ):

        raise HTTPException(
            status_code=502,
            detail=(
                "The AI response did not contain "
                "a valid questions array."
            ),
        )

    if len(questions) != expected_count:

        raise HTTPException(
            status_code=502,
            detail=(
                f"The AI generated {len(questions)} "
                f"questions instead of {expected_count}."
            ),
        )

    validated = []

    for index, question in enumerate(
        questions,
        start=expected_start,
    ):

        if not isinstance(
            question,
            dict,
        ):

            raise HTTPException(
                status_code=502,
                detail=(
                    f"Question q{index} "
                    f"has an invalid format."
                ),
            )

        question_id = f"q{index}"

        question_text = str(
            question.get(
                "question",
                "",
            )
        ).strip()

        options = question.get(
            "options"
        )

        correct_answer = str(
            question.get(
                "correct_answer",
                "",
            )
        ).strip()

        if not question_text:

            raise HTTPException(
                status_code=502,
                detail=(
                    f"Question q{index} is empty."
                ),
            )

        if not isinstance(
            options,
            list,
        ):

            raise HTTPException(
                status_code=502,
                detail=(
                    f"Question q{index} "
                    f"has invalid options."
                ),
            )

        if len(options) != 4:

            raise HTTPException(
                status_code=502,
                detail=(
                    f"Question q{index} must "
                    f"have exactly 4 options."
                ),
            )

        options = [
            str(option).strip()
            for option in options
        ]

        if any(
            not option
            for option in options
        ):

            raise HTTPException(
                status_code=502,
                detail=(
                    f"Question q{index} "
                    f"contains an empty option."
                ),
            )

        if len(set(options)) != 4:

            raise HTTPException(
                status_code=502,
                detail=(
                    f"Question q{index} "
                    f"contains duplicate options."
                ),
            )

        if correct_answer not in options:

            raise HTTPException(
                status_code=502,
                detail=(
                    f"Question q{index} "
                    f"has an invalid correct answer."
                ),
            )

        validated.append(
            {
                "id": question_id,
                "question": question_text,
                "options": options,
                "correct_answer": correct_answer,
            }
        )

    return validated


# ============================================================
# GENERATE BATCH
# ============================================================


def generate_batch(
    degree: str,
    subject: str,
    topic: str,
    difficulty: str,
    start_number: int,
    end_number: int,
):

    system_prompt = """
You are ConceptBridge's educational assessment engine.

Generate accurate multiple-choice questions.

Return ONLY valid JSON.
Never return Markdown.
Never add commentary outside the JSON.
Keep the output concise.
"""

    user_prompt = build_batch_prompt(
        degree=degree,
        subject=subject,
        topic=topic,
        difficulty=difficulty,
        start_number=start_number,
        end_number=end_number,
    )

    try:

        routed = generate_with_routing(
            requested_provider="auto",
            system_prompt=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
            allow_fallback=True,
        )

    except RoutingError as exc:

        raise HTTPException(
            status_code=502,
            detail={
                "message": str(exc),
                "route_events": exc.route_events,
            },
        ) from None

    except ProviderError as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from None

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                f"AI generation failed: {str(exc)}"
            ),
        ) from None

    return parse_batch_response(
        routed.result.text,
        start_number,
        end_number - start_number + 1,
    )


# ============================================================
# GENERATE COMPLETE 15-QUESTION TEST
# ============================================================


@router.post(
    "/practice-tests/generate",
    status_code=201,
)
def generate_practice_test(
    payload: PracticeTestGenerateRequest,
    current_user: User = Depends(get_current_user),
):

    degree = payload.degree.strip()
    subject = payload.subject.strip()
    topic = payload.topic.strip()
    difficulty = payload.difficulty.strip()

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

    if difficulty not in {
        "Easy",
        "Medium",
        "Hard",
    }:

        raise HTTPException(
            status_code=422,
            detail=(
                "Difficulty must be "
                "Easy, Medium or Hard."
            ),
        )

    # ========================================================
    # GENERATE 15 QUESTIONS
    # ========================================================

    questions = []

    questions.extend(
        generate_batch(
            degree,
            subject,
            topic,
            difficulty,
            1,
            5,
        )
    )

    questions.extend(
        generate_batch(
            degree,
            subject,
            topic,
            difficulty,
            6,
            10,
        )
    )

    questions.extend(
        generate_batch(
            degree,
            subject,
            topic,
            difficulty,
            11,
            15,
        )
    )

    if len(questions) != 15:

        raise HTTPException(
            status_code=502,
            detail=(
                "Practice test generation "
                f"produced {len(questions)} "
                "questions instead of 15."
            ),
        )

    # ========================================================
    # CREATE TEST
    # ========================================================

    test_id = str(
        uuid.uuid4()
    )

    PRACTICE_TESTS[test_id] = {
        "test_id": test_id,
        "user_id": str(current_user.id),
        "degree": degree,
        "subject": subject,
        "topic": topic,
        "difficulty": difficulty,
        "questions": questions,
    }

    # ========================================================
    # HIDE CORRECT ANSWERS
    # ========================================================

    public_questions = [
        {
            "id": question["id"],
            "question": question["question"],
            "options": question["options"],
        }
        for question in questions
    ]

    return {
        "test_id": test_id,
        "degree": degree,
        "subject": subject,
        "topic": topic,
        "difficulty": difficulty,
        "total_questions": 15,
        "questions": public_questions,
    }


# ============================================================
# GET TEST
# ============================================================


@router.get(
    "/practice-tests/{test_id}"
)
def get_practice_test(
    test_id: str,
    current_user: User = Depends(get_current_user),
):

    test = PRACTICE_TESTS.get(
        test_id
    )

    if not test:

        raise HTTPException(
            status_code=404,
            detail=(
                "Practice test was not found "
                "or has expired."
            ),
        )

    # ========================================================
    # AUTHORIZATION CHECK
    # ========================================================

    if test["user_id"] != str(
        current_user.id
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "You do not have access "
                "to this practice test."
            ),
        )

    return {
        "test_id": test["test_id"],
        "degree": test["degree"],
        "subject": test["subject"],
        "topic": test["topic"],
        "difficulty": test["difficulty"],
        "total_questions": 15,
        "questions": [
            {
                "id": question["id"],
                "question": question["question"],
                "options": question["options"],
            }
            for question in test["questions"]
        ],
    }


# ============================================================
# SUBMIT TEST
# ============================================================


@router.post(
    "/practice-tests/submit"
)
def submit_practice_test(
    payload: PracticeTestSubmitRequest,
    current_user: User = Depends(get_current_user),
):

    test = PRACTICE_TESTS.get(
        payload.test_id
    )

    if not test:

        raise HTTPException(
            status_code=404,
            detail=(
                "Practice test was not found "
                "or has expired."
            ),
        )

    # ========================================================
    # AUTHORIZATION CHECK
    # ========================================================

    if test["user_id"] != str(
        current_user.id
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "You do not have access "
                "to this practice test."
            ),
        )

    score = 0
    answered = 0

    review = []

    for question in test["questions"]:

        question_id = question["id"]

        user_answer = (
            payload.answers.get(
                question_id,
                "",
            ).strip()
        )

        if user_answer:
            answered += 1

        correct_answer = (
            question["correct_answer"]
        )

        is_correct = (
            user_answer
            == correct_answer
        )

        if is_correct:
            score += 1

        explanation = (
            "The correct answer is "
            f"{correct_answer}."
        )

        review.append(
            {
                "id": question_id,
                "question": question["question"],
                "options": question["options"],
                "your_answer": (
                    user_answer
                    if user_answer
                    else None
                ),
                "correct_answer": correct_answer,
                "correct": is_correct,
                "explanation": explanation,
            }
        )

    percentage = round(
        (score / 15) * 100,
        2,
    )

    return {
        "test_id": test["test_id"],
        "degree": test["degree"],
        "subject": test["subject"],
        "topic": test["topic"],
        "difficulty": test["difficulty"],
        "total_questions": 15,
        "answered": answered,
        "score": score,
        "percentage": percentage,
        "review": review,
    }