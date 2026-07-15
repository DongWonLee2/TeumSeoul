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
    Field(
        min_length=1,
        max_length=1000,
        description="대화 메시지(1~1,000자, 공백만 입력 불가)",
    ),
    AfterValidator(_strip_nonempty),
]


class ChatCurrentLocation(APIModel):
    latitude: float = Field(ge=-90, le=90, description="현재 위치 WGS84 위도")
    longitude: float = Field(ge=-180, le=180, description="현재 위치 WGS84 경도")


class ChatContext(APIModel):
    available_minutes: Literal[30, 60, 120, 240] | None = Field(
        default=None,
        description="사용 가능한 시간(분): 30, 60, 120, 240",
        examples=[120],
    )
    companion: Companion | None = Field(
        default=None,
        description="동행 유형: solo, couple, friends, family",
        examples=["friends"],
    )
    mood: Mood | None = Field(
        default=None,
        description="분위기: healing, culture, activity, night_view, shopping",
        examples=["culture"],
    )
    district: str | None = Field(
        default=None,
        min_length=2,
        max_length=20,
        description="희망 서울 자치구",
        examples=["종로구"],
    )
    current_location: ChatCurrentLocation | None = Field(
        default=None,
        description="거리순 검색에 사용할 선택 현재 위치",
    )


class ChatHistoryItem(APIModel):
    role: ChatRole = Field(description="메시지 작성 역할: user 또는 assistant")
    content: ChatMessage = Field(description="이전 대화 메시지")


class ChatRequest(APIModel):
    message: ChatMessage = Field(
        description="서울 장소 추천 또는 커뮤니티 검색 질문",
        examples=["종로에서 2시간 동안 둘러볼 문화 장소를 추천해줘"],
    )
    context: ChatContext | None = Field(
        default=None,
        description="프론트엔드가 전달하는 선택 검색 조건",
    )
    history: list[ChatHistoryItem] = Field(
        default_factory=list,
        max_length=10,
        description="최근 대화 내역(최대 10개)",
    )


class ChatLocationResult(APIModel):
    location_id: int = Field(description="실제 DB 장소 ID")
    title: str = Field(description="장소명")
    content_type: str = Field(description="콘텐츠 유형 한국어명")
    address: str | None = Field(description="장소 주소")
    reason: str = Field(description="검색 조건과 장소가 일치하는 이유")
    source_modified_at: str | None = Field(description="원천 데이터 최종 수정 시각")


class ChatCommunityPost(APIModel):
    post_id: int = Field(description="실제 DB 게시글 ID")
    title: str = Field(description="커뮤니티 게시글 제목")
    status_tag: str | None = Field(description="게시글 현장 상태 태그")
    location_id: int | None = Field(description="게시글에 연결된 장소 ID")


class ChatResponse(APIModel):
    answer: str = Field(description="검색 근거를 바탕으로 생성한 한국어 답변")
    results: list[ChatLocationResult] = Field(description="추천 장소 결과(기본 최대 3건)")
    community_posts: list[ChatCommunityPost] = Field(
        description="질문 또는 추천 장소와 관련된 커뮤니티 게시글(최대 3건)"
    )
    warnings: list[str] = Field(description="데이터 제약과 폴백 관련 안내")
    extracted_context: dict[str, object] = Field(
        description="자연어 질문과 명시적 context에서 추출한 검색 조건"
    )
    fallback: bool = Field(description="OpenAI 대신 규칙 기반 DB 답변을 사용했는지 여부")


class AIRecommendation(APIModel):
    location_id: int
    reason: str = Field(min_length=1, max_length=300)


class AIChatOutput(APIModel):
    answer: str = Field(min_length=1, max_length=1500)
    recommendations: list[AIRecommendation] = Field(max_length=3)
    post_ids: list[int] = Field(max_length=3)
    warnings: list[str] = Field(default_factory=list, max_length=5)
