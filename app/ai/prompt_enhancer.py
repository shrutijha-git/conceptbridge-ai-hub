from __future__ import annotations

from typing import Any


def enhance_tutor_prompt(
    user_message: str,
    *,
    degree: str | None = None,
    subject: str | None = None,
    topic: str | None = None,
    learning_goal: str | None = None,
    explanation_style: str | None = None,
    notes_context: str | None = None,
    recent_messages: list[dict[str, Any]] | None = None,
) -> str:
    """
    Enhances a student's Tutor question using the current learning context.

    This does NOT call an AI model.
    It prepares a structured prompt for the existing AI provider/router.
    """

    parts: list[str] = []

    parts.append(
        """You are the AI Tutor inside ConceptBridge, a personalized learning platform.

Your job is to help the student understand the CURRENT concept clearly,
accurately, and progressively.

Use the student's learning context below when it is relevant.
Do not invent information that is not supported by the student's notes or
conversation. If the notes do not contain the answer, use your general
knowledge when appropriate and clearly distinguish it from the uploaded
material.

TEACHING PRINCIPLES:
- Explain at the student's academic level.
- Start with intuition before technical detail when possible.
- Use simple language without becoming inaccurate.
- Give examples when they improve understanding.
- Connect the answer to the current topic.
- Respect the student's stated learning goal.
- Avoid unnecessarily long answers.
- If the student seems confused, break the concept into smaller steps.
- If useful, finish with a short check-for-understanding question.
"""
    )

    if degree:
        parts.append(f"STUDENT DEGREE:\n{degree}")

    if subject:
        parts.append(f"SUBJECT:\n{subject}")

    if topic:
        parts.append(f"CURRENT TOPIC:\n{topic}")

    if learning_goal:
        parts.append(f"LEARNING GOAL:\n{learning_goal}")

    if explanation_style:
        parts.append(f"STUDENT'S PREFERRED EXPLANATION STYLE:\n{explanation_style}")

    if notes_context:
        parts.append(
            f"""UPLOADED STUDY MATERIAL:

{notes_context}

Use this material when answering questions about the student's current topic.
"""
        )

    if recent_messages:
        conversation_lines: list[str] = []

        for message in recent_messages[-8:]:
            role = str(message.get("role", "user")).upper()
            content = str(message.get("content", "")).strip()

            if content:
                conversation_lines.append(
                    f"{role}: {content}"
                )

        if conversation_lines:
            parts.append(
                "RECENT CONVERSATION:\n"
                + "\n".join(conversation_lines)
            )

    parts.append(
        f"""STUDENT'S CURRENT QUESTION:

{user_message.strip()}

Now answer the student's question as their ConceptBridge Tutor."""
    )

    return "\n\n---\n\n".join(parts)