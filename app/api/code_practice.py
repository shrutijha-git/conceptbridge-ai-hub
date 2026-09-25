import json
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.ai.router import generate_with_routing, RoutingError
from app.ai.providers.base import ProviderError


router = APIRouter()

CODE_CHALLENGES = {}


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class CodeChallengeGenerateRequest(BaseModel):
    degree: str = Field(min_length=1, max_length=150)
    subject: str = Field(min_length=1, max_length=150)
    topic: str = Field(min_length=1, max_length=255)
    language: str = Field(default="Python", min_length=1, max_length=50)


class CodeSolutionSubmitRequest(BaseModel):
    challenge_id: str = Field(min_length=1)
    code: str = Field(min_length=1, max_length=30000)


# ============================================================
# GENERATION PROMPT
# ============================================================

def build_code_prompt(
    degree: str,
    subject: str,
    topic: str,
    language: str,
):
    return f"""
You are ConceptBridge's coding-practice generator.

Create ONE educational coding challenge for:

Degree: {degree}
Subject: {subject}
Topic: {topic}
Programming language: {language}

Requirements:

1. The challenge must be appropriate for the academic level.
2. It must be directly related to the supplied subject and topic.
3. Make the task practical and educational.
4. Keep the problem concise.
5. Provide a clear problem statement.
6. Provide 3 to 5 requirements.
7. Provide a small example input and output where applicable.
8. Provide starter code.
9. Do not provide the complete solution.
10. Do not reveal the answer.
11. Return ONLY valid JSON.
12. Do not use Markdown outside the JSON.

Use exactly this structure:

{{
  "title": "Challenge title",
  "description": "Clear problem description",
  "requirements": [
    "Requirement 1",
    "Requirement 2",
    "Requirement 3"
  ],
  "example_input": "Example input",
  "example_output": "Example output",
  "starter_code": "Starter code",
  "hints": [
    "Hint 1",
    "Hint 2"
  ]
}}
"""


# ============================================================
# PARSE GENERATION RESPONSE
# ============================================================

def parse_challenge(content: str):

    content = content.strip()

    if content.startswith("```"):
        lines = content.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        content = "\n".join(lines).strip()

    try:
        data = json.loads(content)

    except json.JSONDecodeError:

        raise HTTPException(
            status_code=502,
            detail="The AI returned invalid JSON for the coding challenge.",
        ) from None

    required_fields = [
        "title",
        "description",
        "requirements",
        "example_input",
        "example_output",
        "starter_code",
        "hints",
    ]

    for field in required_fields:

        if field not in data:

            raise HTTPException(
                status_code=502,
                detail=f"The AI response is missing '{field}'.",
            )

    if not isinstance(data["requirements"], list):
        raise HTTPException(
            status_code=502,
            detail="Challenge requirements must be a list.",
        )

    if not isinstance(data["hints"], list):
        raise HTTPException(
            status_code=502,
            detail="Challenge hints must be a list.",
        )

    return {
        "title": str(data["title"]).strip(),
        "description": str(data["description"]).strip(),
        "requirements": [
            str(item).strip()
            for item in data["requirements"]
        ],
        "example_input": str(data["example_input"]),
        "example_output": str(data["example_output"]),
        "starter_code": str(data["starter_code"]),
        "hints": [
            str(item).strip()
            for item in data["hints"]
        ],
    }


# ============================================================
# GENERATE CHALLENGE
# ============================================================

@router.post(
    "/code-practice/generate",
    status_code=201,
)
def generate_code_challenge(
    payload: CodeChallengeGenerateRequest,
):

    degree = payload.degree.strip()
    subject = payload.subject.strip()
    topic = payload.topic.strip()
    language = payload.language.strip()

    system_prompt = """
You are ConceptBridge's coding education engine.

Generate concise, accurate coding challenges.

Return valid JSON only.
Do not return Markdown outside JSON.
Do not provide the complete solution.
"""

    user_prompt = build_code_prompt(
        degree=degree,
        subject=subject,
        topic=topic,
        language=language,
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
            detail=f"AI generation failed: {str(exc)}",
        ) from None

    challenge = parse_challenge(
        routed.result.text
    )

    challenge_id = str(uuid.uuid4())

    CODE_CHALLENGES[challenge_id] = {
        "challenge_id": challenge_id,
        "degree": degree,
        "subject": subject,
        "topic": topic,
        "language": language,
        **challenge,
    }

    return {
        "challenge_id": challenge_id,
        "degree": degree,
        "subject": subject,
        "topic": topic,
        "language": language,
        "title": challenge["title"],
        "description": challenge["description"],
        "requirements": challenge["requirements"],
        "example_input": challenge["example_input"],
        "example_output": challenge["example_output"],
        "starter_code": challenge["starter_code"],
        "hints": challenge["hints"],
    }


# ============================================================
# SUBMIT SOLUTION
# ============================================================

@router.post(
    "/code-practice/submit"
)
def submit_code_solution(
    payload: CodeSolutionSubmitRequest,
):

    challenge = CODE_CHALLENGES.get(
        payload.challenge_id
    )

    if not challenge:

        raise HTTPException(
            status_code=404,
            detail="Coding challenge was not found or has expired.",
        )

    code = payload.code.strip()

    if not code:

        raise HTTPException(
            status_code=422,
            detail="Write some code before submitting.",
        )

    system_prompt = """
You are ConceptBridge's coding evaluator.

Evaluate a student's submitted solution against the
coding challenge.

Do not execute the code.

Analyze the code logically.

Return ONLY valid JSON.

Use exactly:

{
  "score": 0,
  "correct": false,
  "summary": "Short assessment",
  "strengths": [
    "Strength"
  ],
  "issues": [
    "Issue"
  ],
  "suggestions": [
    "Suggestion"
  ],
  "explanation": "Detailed educational explanation"
}

Score must be an integer from 0 to 100.
"""

    user_prompt = f"""
CODING CHALLENGE

Degree:
{challenge["degree"]}

Subject:
{challenge["subject"]}

Topic:
{challenge["topic"]}

Language:
{challenge["language"]}

Title:
{challenge["title"]}

Problem:
{challenge["description"]}

Requirements:
{json.dumps(challenge["requirements"])}

Expected example input:
{challenge["example_input"]}

Expected example output:
{challenge["example_output"]}

STARTER CODE:
{challenge["starter_code"]}

STUDENT SUBMISSION:
{code}

Evaluate whether the student's code logically solves
the problem and satisfies the requirements.

Do not execute the code.
"""

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
            detail=f"AI evaluation failed: {str(exc)}",
        ) from None

    content = routed.result.text.strip()

    if content.startswith("```"):

        lines = content.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        content = "\n".join(lines).strip()

    try:

        result = json.loads(content)

    except json.JSONDecodeError:

        raise HTTPException(
            status_code=502,
            detail="The AI returned invalid evaluation data.",
        ) from None

    score = result.get("score", 0)

    try:
        score = int(score)
    except (TypeError, ValueError):
        score = 0

    score = max(0, min(100, score))

    return {
        "challenge_id": payload.challenge_id,
        "score": score,
        "correct": bool(result.get("correct", False)),
        "summary": str(
            result.get("summary", "")
        ),
        "strengths": result.get(
            "strengths",
            [],
        ),
        "issues": result.get(
            "issues",
            [],
        ),
        "suggestions": result.get(
            "suggestions",
            [],
        ),
        "explanation": str(
            result.get("explanation", "")
        ),
    }