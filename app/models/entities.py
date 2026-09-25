from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def utcnow():
    # MySQL DATETIME stores naive UTC; create it explicitly from aware UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None)

def uuid_str() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str
    )

    name: Mapped[str] = mapped_column(
        String(120)
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True
    )

    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    plan: Mapped[str] = mapped_column(
        String(30),
        default="free"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow
    )


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    degree: Mapped[str] = mapped_column(String(50))
    subject: Mapped[str] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LearningSession(Base):
    __tablename__ = "learning_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), index=True)
    current_topic: Mapped[str] = mapped_column(String(255))
    current_provider: Mapped[str] = mapped_column(String(30), default="mock")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("learning_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(String(30), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class LearningState(Base):
    __tablename__ = "learning_state"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), index=True)
    concept: Mapped[str] = mapped_column(String(255), index=True)
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    weakness: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Mistake(Base):
    __tablename__ = "mistakes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("learning_sessions.id"), index=True)
    concept: Mapped[str] = mapped_column(String(255))
    mistake_type: Mapped[str] = mapped_column(String(120))
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    embedding_status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AIUsage(Base):
    __tablename__ = "ai_usage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("learning_sessions.id"), index=True)
    provider: Mapped[str] = mapped_column(String(30))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

# Additive v0.2 tables. Existing starter tables and rows are left intact.
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.mysql import DATETIME
precise_datetime = DateTime().with_variant(DATETIME(fsp=6), "mysql")

class SessionMemory(Base):
    __tablename__ = 'session_memory'
    session_id: Mapped[str] = mapped_column(ForeignKey('learning_sessions.id'), primary_key=True)
    state_json: Mapped[str] = mapped_column(Text, default='{}')
    next_turn: Mapped[int] = mapped_column(Integer, default=1)
    summary_through_turn: Mapped[int] = mapped_column(Integer, default=0)

class ChatTurn(Base):
    __tablename__ = 'chat_turns'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    session_id: Mapped[str] = mapped_column(ForeignKey('learning_sessions.id'), index=True)
    turn_no: Mapped[int] = mapped_column(Integer)
    user_message_id: Mapped[str] = mapped_column(ForeignKey('messages.id'))
    assistant_message_id: Mapped[str] = mapped_column(ForeignKey('messages.id'))
    response_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(precise_datetime, default=utcnow)
    __table_args__ = (UniqueConstraint('session_id','turn_no',name='uq_session_turn'),)

class ProviderCall(Base):
    __tablename__ = 'provider_calls'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey('learning_sessions.id'), index=True)
    turn_id: Mapped[str] = mapped_column(ForeignKey('chat_turns.id'))
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(120))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    route_events_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(precise_datetime, default=utcnow)

class SessionDocument(Base):
    __tablename__ = 'session_documents'
    session_id: Mapped[str] = mapped_column(ForeignKey('learning_sessions.id'), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey('documents.id'), primary_key=True)

class DocumentChunk(Base):
    __tablename__ = 'document_chunks'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    document_id: Mapped[str] = mapped_column(ForeignKey('documents.id'), index=True)
    chunk_no: Mapped[int] = mapped_column(Integer)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text)

class PracticeAttempt(Base):
    __tablename__ = 'practice_attempts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey('learning_sessions.id'), index=True)
    concept: Mapped[str] = mapped_column(String(255))
    mode: Mapped[str] = mapped_column(String(30))
    question_id: Mapped[str] = mapped_column(String(100))
    answer: Mapped[str] = mapped_column(Text)
    feedback_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(precise_datetime, default=utcnow)

class VideoSegment(Base):
    __tablename__ = 'video_segments'

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey('learning_sessions.id'),
        index=True
    )

    video_id: Mapped[str] = mapped_column(
        String(11)
    )

    title: Mapped[str] = mapped_column(
        String(255)
    )

    topic: Mapped[str] = mapped_column(
        String(255)
    )

    start_seconds: Mapped[int] = mapped_column(
        Integer
    )

    end_seconds: Mapped[int] = mapped_column(
        Integer
    )

    evidence: Mapped[str] = mapped_column(
        Text
    )

    verification: Mapped[str] = mapped_column(
        String(40),
        default='user_supplied'
    )

    created_at: Mapped[datetime] = mapped_column(
        precise_datetime,
        default=utcnow
    )


class VideoBookmark(Base):
    __tablename__ = 'video_bookmarks'

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid_str
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey('learning_sessions.id'),
        index=True
    )

    video_id: Mapped[str] = mapped_column(
        String(11)
    )

    timestamp_seconds: Mapped[int] = mapped_column(
        Integer
    )

    note: Mapped[str] = mapped_column(
        Text
    )

    created_at: Mapped[datetime] = mapped_column(
        precise_datetime,
        default=utcnow
    )


class DataAnalysis(Base):
    """Saved calculated results. Original CSV bytes are not retained."""

    __tablename__ = 'data_analyses'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey('learning_sessions.id'), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    choices_json: Mapped[dict] = mapped_column(JSON)
    result_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(precise_datetime, default=utcnow, index=True)
