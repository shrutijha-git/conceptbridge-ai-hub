from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

ProviderName = Literal['auto', 'mock', 'openai', 'gemini', 'anthropic']

class DemoSessionRequest(BaseModel):
    degree: Literal['MCA','BCA','MBA','BBA'] = 'MCA'
    subject: str = Field(default='DBMS', min_length=1, max_length=150)
    topic: str = Field(default='Third Normal Form', min_length=1, max_length=255)
    @field_validator('subject','topic')
    @classmethod
    def not_blank(cls, v):
        if not v.strip(): raise ValueError('Must not be blank')
        return v.strip()

class DemoSessionResponse(BaseModel):
    session_id: str
    user_id: str
    course_id: str

class ChatRequest(BaseModel):
    session_id: UUID
    request_id: UUID | None = None
    message: str = Field(min_length=1, max_length=12000)
    provider: ProviderName = 'auto'
    allow_fallback: bool = False
    mode: Literal['understand','practise','code'] = 'understand'
    @field_validator('message')
    @classmethod
    def not_blank(cls, v):
        if not v.strip(): raise ValueError('Message must not be blank')
        return v.strip()

class ChatResponse(BaseModel):
    session_id: str
    request_id: str
    provider_requested: str
    provider_used: str
    previous_provider: str | None
    provider_changed: bool
    fallback_used: bool
    is_mock: bool
    response: str
    turn_no: int
    route_events: list[dict]
    usage: dict
    context: dict

class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    provider: str | None = None
    sequence: int

class MemoryPatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    learning_objective: str = Field(default='', max_length=600)
    current_question: str = Field(default='', max_length=1000)
    known_concepts: list[str] = Field(default_factory=list, max_length=15)
    weak_concepts: list[str] = Field(default_factory=list, max_length=15)
    misconceptions: list[str] = Field(default_factory=list, max_length=15)
    explanation_preference: str = Field(default='Worked examples', max_length=200)
    @field_validator('known_concepts','weak_concepts','misconceptions')
    @classmethod
    def short_items(cls, items):
        if any(not x.strip() or len(x)>200 for x in items): raise ValueError('Use non-empty items up to 200 characters')
        return items

class AttemptRequest(BaseModel):
    session_id: UUID
    question_id: str = Field(min_length=1, max_length=100)
    answer: str = Field(min_length=1, max_length=12000)

class VideoCreate(BaseModel):
    session_id: UUID
    video_id: str = Field(pattern=r'^[A-Za-z0-9_-]{11}$')
    title: str = Field(min_length=1, max_length=255)
    topic: str = Field(min_length=1, max_length=255)
    start_seconds: int = Field(ge=0, le=86400)
    end_seconds: int = Field(gt=0, le=86400)
    evidence: str = Field(min_length=20, max_length=4000)
    @model_validator(mode='after')
    def valid_interval(self):
        if self.end_seconds <= self.start_seconds: raise ValueError('End must be after start')
        return self
class VideoBookmarkCreate(BaseModel):
    session_id: UUID
    video_id: str = Field(
        pattern=r'^[A-Za-z0-9_\-]{11}$'
    )
    timestamp_seconds: int = Field(
        ge=0,
        le=86400
    )
    note: str = Field(
        min_length=1,
        max_length=1000
    )