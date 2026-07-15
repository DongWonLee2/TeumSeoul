from typing import Annotated, Literal

from pydantic import AfterValidator, Field

from app.schemas.common import APIModel

ChatRole = Literal["user", "assistant"]
Companion = Literal["solo", "couple", "friends", "family"]
Mood = Literal["healing", "culture", "activity", "night_view", "shopping"]


def _strip_nonempty(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("공백만 입력할 수 없습니다.")
    return normalized


ChatMessage = Annotated[
    str,
    Field(min_length=1, max_length=1000),
    AfterValidator(_strip_nonempty),
]


class ChatCurrentLocation(APIModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ChatContext(APIModel):
    available_minutes: Literal[30, 60, 120, 240] | None = None
    companion: Companion | None = None
    mood: Mood | None = None
    district: str | None = Field(default=None, min_length=2, max_length=20)
    current_location: ChatCurrentLocation | None = None


class ChatHistoryItem(APIModel):
    role: ChatRole
    content: ChatMessage


class ChatRequest(APIModel):
    message: ChatMessage
    context: ChatContext | None = None
    history: list[ChatHistoryItem] = Field(default_factory=list, max_length=10)


class ChatLocationResult(APIModel):
    location_id: int
    title: str
    content_type: str
    address: str | None
    reason: str
    source_modified_at: str | None


class ChatCommunityPost(APIModel):
    post_id: int
    title: str
    status_tag: str | None
    location_id: int | None


class ChatResponse(APIModel):
    answer: str
    results: list[ChatLocationResult]
    community_posts: list[ChatCommunityPost]
    warnings: list[str]
    extracted_context: dict[str, object]
    fallback: bool


class AIRecommendation(APIModel):
    location_id: int
    reason: str = Field(min_length=1, max_length=300)


class AIChatOutput(APIModel):
    answer: str = Field(min_length=1, max_length=1500)
    recommendations: list[AIRecommendation] = Field(max_length=3)
    post_ids: list[int] = Field(max_length=3)
    warnings: list[str] = Field(default_factory=list, max_length=5)
