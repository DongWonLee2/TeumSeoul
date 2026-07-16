from collections.abc import Generator
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.location import Location
from app.models.mixins import utc_now
from app.models.post import Post
from app.repositories.chat import LocationCandidate, PostCandidate
from app.schemas.chat import AIChatOutput, AIRecommendation, ChatRequest
from app.services.chat import ExtractedContext, generate_ai_output, handle_chat


@pytest.fixture
def chat_api() -> Generator[tuple[TestClient, Session], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app: FastAPI = create_app()
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=False)
    yield client, db
    client.close()
    db.close()
    Base.metadata.drop_all(engine)


def add_location(
    db: Session,
    *,
    title: str,
    content_type_id: int,
    district: str = "종로구",
    latitude: float = 37.57,
    longitude: float = 126.98,
) -> Location:
    now = utc_now()
    location = Location(
        source_content_id=f"chat-{content_type_id}-{title}",
        content_type_id=content_type_id,
        title=title,
        address=f"서울특별시 {district}",
        district=district,
        latitude=latitude,
        longitude=longitude,
        image_url=None,
        thumbnail_url=None,
        telephone=None,
        copyright_code=None,
        category_code_1=None,
        category_code_2=None,
        category_code_3=None,
        classification_code_1=None,
        classification_code_2=None,
        classification_code_3=None,
        source_created_at=now,
        source_modified_at=now,
        raw_json="{}",
    )
    db.add(location)
    db.commit()
    return location


def test_chat_without_api_key_returns_database_fallback(chat_api, monkeypatch) -> None:
    client, db = chat_api
    location = add_location(db, title="종로 문화 공간", content_type_id=14)
    monkeypatch.setattr(settings, "openai_api_key", None)

    response = client.post(
        "/api/chat",
        json={
            "message": "종로에서 2시간, 친구와 조용한 문화 분위기로 추천해줘",
            "context": {
                "available_minutes": 120,
                "companion": "friends",
                "mood": "culture",
                "district": "종로구",
                "current_location": None,
            },
            "history": [],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["fallback"] is True
    assert body["data"]["results"][0]["location_id"] == location.id
    assert body["data"]["extracted_context"]["available_minutes"] == 120
    assert body["data"]["extracted_context"]["district"] == "종로구"
    assert "meta" not in body


def test_chat_validates_ai_ids_and_returns_community_posts(chat_api) -> None:
    _, db = chat_api
    location = add_location(db, title="아트센터", content_type_id=14)
    post = Post(
        location_id=location.id,
        category="방문 후기",
        status_tag="혼자 추천",
        title="최근 방문 팁",
        content="오전에는 비교적 여유로웠습니다.",
        password="1234",
    )
    db.add(post)
    db.commit()

    def fake_ai(**kwargs) -> AIChatOutput:
        candidates = kwargs["candidates"]
        posts = kwargs["posts"]
        assert candidates[0].id == location.id
        assert posts[0].content == "오전에는 비교적 여유로웠습니다."
        return AIChatOutput(
            answer="DB 후보를 바탕으로 안내합니다.",
            recommendations=[
                AIRecommendation(location_id=location.id, reason="문화 조건과 일치합니다."),
                AIRecommendation(location_id=999999, reason="존재하지 않는 후보"),
            ],
            post_ids=[post.id, 999999],
            warnings=[],
        )

    result = handle_chat(
        db,
        ChatRequest(
            message="종로구 문화 장소와 최근 후기를 추천해줘",
            context={"district": "종로구", "mood": "culture"},
        ),
        ai_generator=fake_ai,
    )

    assert result.fallback is False
    assert [item.location_id for item in result.results] == [location.id]
    assert [item.post_id for item in result.community_posts] == [post.id]


def test_chat_invalid_ai_candidate_ids_trigger_fallback(chat_api) -> None:
    _, db = chat_api
    location = add_location(db, title="문화 후보", content_type_id=14)

    def invalid_ai(**kwargs) -> AIChatOutput:
        return AIChatOutput(
            answer="잘못된 후보",
            recommendations=[AIRecommendation(location_id=999999, reason="잘못된 ID")],
            post_ids=[],
            warnings=[],
        )

    result = handle_chat(
        db,
        ChatRequest(message="종로구 문화 장소 추천", context={"district": "종로구"}),
        ai_generator=invalid_ai,
    )

    assert result.fallback is True
    assert result.results[0].location_id == location.id


@pytest.mark.parametrize(
    ("message", "content_type_id", "warning_text"),
    [
        ("오늘 종로에서 열리는 축제 알려줘", 15, "행사 일정"),
        ("지금 영업 중인 곳 알려줘", 14, "운영시간"),
        ("가장 싼 호텔 알려줘", 32, "가격"),
        ("정확히 2시간 걸리는 최적 동선 추천해줘", 25, "최적 경로"),
    ],
)
def test_chat_restricted_queries_use_safe_database_response(
    chat_api, message: str, content_type_id: int, warning_text: str
) -> None:
    _, db = chat_api
    add_location(db, title=f"제한 질의 후보 {content_type_id}", content_type_id=content_type_id)

    def must_not_call_ai(**kwargs) -> AIChatOutput:
        raise AssertionError("제한 질의에서 OpenAI를 호출하면 안 됩니다.")

    result = handle_chat(
        db,
        ChatRequest(message=message),
        ai_generator=must_not_call_ai,
    )

    assert result.fallback is False
    assert warning_text in result.warnings[0]
    assert result.results
    assert all(item.location_id > 0 for item in result.results)


def test_chat_validation_uses_chat_error_code(chat_api) -> None:
    client, _ = chat_api
    blank = client.post("/api/chat", json={"message": "   ", "history": []})
    assert blank.status_code == 422
    assert blank.json()["code"] == "INVALID_CHAT_INPUT"

    too_much_history = client.post(
        "/api/chat",
        json={
            "message": "추천해줘",
            "history": [{"role": "user", "content": "이전 질문"}] * 11,
        },
    )
    assert too_much_history.status_code == 422
    assert too_much_history.json()["code"] == "INVALID_CHAT_INPUT"


def test_chat_openapi_responses_do_not_expose_secrets(chat_api) -> None:
    client, _ = chat_api
    schema = client.get("/api/openapi.json").json()
    response_properties = schema["components"]["schemas"]["ChatResponse"]["properties"]
    assert "password" not in str(response_properties)
    assert "api_key" not in str(response_properties)
    assert settings.openai_api_key is None or isinstance(settings.openai_api_key, SecretStr)


def test_openai_structured_output_uses_bounded_redacted_evidence(monkeypatch) -> None:
    captured: dict[str, object] = {}
    parsed_output = AIChatOutput(
        answer="구조화된 답변",
        recommendations=[AIRecommendation(location_id=1, reason="검증된 이유")],
        post_ids=[2],
        warnings=[],
    )

    class FakeResponses:
        def parse(self, **kwargs):
            captured["request"] = kwargs
            return type("Response", (), {"output_parsed": parsed_output})()

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.responses = FakeResponses()

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("sk-test-secret-123456789"))
    candidate = LocationCandidate(
        id=1,
        content_type_id=14,
        title="문화 공간",
        address="서울특별시 종로구",
        district="종로구",
        latitude=37.5,
        longitude=127.0,
        source_modified_at=datetime(2026, 7, 14),
    )
    post = PostCandidate(
        id=2,
        location_id=1,
        title="현장 후기",
        content="가" * 400,
        status_tag="혼자 추천",
    )

    output = generate_ai_output(
        payload=ChatRequest(
            message="api_key=secret 종로 문화를 추천해줘",
            history=[{"role": "user", "content": "sk-history-secret-123456789"}],
        ),
        context=ExtractedContext(district="종로구"),
        candidates=[candidate],
        posts=[post],
    )

    assert output == parsed_output
    assert captured["client"]["timeout"] == settings.openai_timeout_seconds
    request = captured["request"]
    assert request["model"] == "gpt-5-mini"
    assert request["text_format"] is AIChatOutput
    assert request["reasoning"] == {"effort": "low"}
    assert request["max_output_tokens"] == 3000
    assert request["store"] is False
    serialized_input = str(request["input"])
    assert "sk-history-secret" not in serialized_input
    assert "api_key=secret" not in serialized_input
    assert "가" * 300 in serialized_input
    assert "가" * 301 not in serialized_input


def test_chat_database_failure_uses_service_unavailable_error(
    chat_api, monkeypatch
) -> None:
    client, _ = chat_api

    def fail_search(*args, **kwargs):
        raise OperationalError("SELECT", {}, Exception("database unavailable"))

    monkeypatch.setattr("app.repositories.chat.search_locations", fail_search)
    response = client.post("/api/chat", json={"message": "서울 장소 추천해줘"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "챗봇 검색 서비스를 사용할 수 없습니다.",
        "code": "CHAT_SERVICE_UNAVAILABLE",
    }
