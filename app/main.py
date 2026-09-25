from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import router
from app.api.learning import router as learning_router
from app.api.code_practice import router as code_practice_router
from app.api.practice_test import router as practice_test_router
from app.api.curriculum import router as curriculum_router
from app.api.auth import router as auth_router

from app.core.config import get_settings
from app.db.database import Base, engine

import app.models.entities


def create_app(initialize_database=True):

    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app):

        if settings.app_env != "development":
            raise RuntimeError(
                "This build is a local development MVP. "
                "Add authentication and authorization before production use."
            )

        if initialize_database:
            try:
                Base.metadata.create_all(bind=engine)
            except SQLAlchemyError:
                print(
                    "MySQL is not ready. Check the database configuration; "
                    "/api/v1/ready reports readiness."
                )

        yield

    app = FastAPI(
        title=settings.app_name,
        version="0.2.0",
        description=(
            "Local ConceptBridge backend: MySQL sessions, provider routing, "
            "learning memory, practice, notes, curated video segments, "
            "and AI-generated practice tests."
        ),
        lifespan=lifespan,
    )

    origins = [
        s.strip()
        for s in settings.allowed_origins.split(",")
        if s.strip()
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=[
            "GET",
            "POST",
            "PATCH",
            "DELETE",
            "OPTIONS",
        ],
        allow_headers=[
            "Content-Type",
            "Authorization",
        ],
    )

    @app.middleware("http")
    async def local_origin_boundary(request: Request, call_next):

        origin = request.headers.get("origin")

        if (
            origin
            and origin not in origins
            and origin != str(request.base_url).rstrip("/")
        ):
            return JSONResponse(
                status_code=403,
                content={"detail": "Origin not allowed."},
            )

        return await call_next(request)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):

        return JSONResponse(
            status_code=503,
            content={
                "detail": (
                    "Database operation failed. Check MySQL availability "
                    "and retry with the same request_id when sending chat."
                )
            },
        )

    app.include_router(
        router,
        prefix=settings.api_prefix,
    )

    app.include_router(
        auth_router,
        prefix=settings.api_prefix,
    )

    app.include_router(
        learning_router,
        prefix=settings.api_prefix,
    )

    app.include_router(
        practice_test_router,
        prefix=settings.api_prefix,
    )

    app.include_router(
        code_practice_router,
        prefix=settings.api_prefix,
    )

    app.include_router(
        curriculum_router,
        prefix=settings.api_prefix,
    )

    return app


app = create_app()