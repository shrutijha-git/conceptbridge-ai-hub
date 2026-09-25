from fastapi import APIRouter, HTTPException

from app.learning.curriculum import CURRICULUM


router = APIRouter()


@router.get("/curriculum/degrees")
def get_degrees():
    return {
        "degrees": [
            *CURRICULUM.keys(),
            "Other"
        ]
    }


@router.get("/curriculum/{degree}/subjects")
def get_subjects(degree: str):

    degree_key = degree.strip()

    if degree_key.lower() == "other":
        return {
            "degree": degree,
            "subjects": ["Other"]
        }

    matched_degree = next(
        (
            key
            for key in CURRICULUM
            if key.casefold() == degree_key.casefold()
        ),
        None
    )

    if not matched_degree:
        raise HTTPException(
            status_code=404,
            detail=f"No subjects found for degree '{degree}'."
        )

    return {
        "degree": matched_degree,
        "subjects": [
            *CURRICULUM[matched_degree].keys(),
            "Other"
        ]
    }


@router.get("/curriculum/{degree}/{subject}/topics")
def get_topics(
    degree: str,
    subject: str
):

    if subject.strip().casefold() == "other":
        return {
            "degree": degree,
            "subject": subject,
            "topics": ["Other"]
        }

    matched_degree = next(
        (
            key
            for key in CURRICULUM
            if key.casefold() == degree.strip().casefold()
        ),
        None
    )

    if not matched_degree:
        raise HTTPException(
            status_code=404,
            detail=f"Degree '{degree}' was not found."
        )

    matched_subject = next(
        (
            key
            for key in CURRICULUM[matched_degree]
            if key.casefold() == subject.strip().casefold()
        ),
        None
    )

    if not matched_subject:
        raise HTTPException(
            status_code=404,
            detail=f"Subject '{subject}' was not found."
        )

    return {
        "degree": matched_degree,
        "subject": matched_subject,
        "topics": [
            *CURRICULUM[matched_degree][matched_subject],
            "Other"
        ]
    }