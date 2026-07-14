from collections.abc import Iterator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.location import Location
from app.schemas.recommendation import (
    AICourse,
    AICourseSelection,
    SituationalRecommendationRequest,
)
from app.services import recommendation as recommendation_service

DISTRICTS = ("종로구", "강남구", "마포구", "송파구")
CONTENT_TYPE_IDS = (12, 14, 15, 25, 28, 38)


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        locations: list[Location] = []
        index = 0
        for district_index, district in enumerate(DISTRICTS):
            for content_type_id in CONTENT_TYPE_IDS:
                for sequence in range(4):
                    index += 1
                    locations.append(
                        _location(
                            source_content_id=f"recommend-{index}",
                            content_type_id=content_type_id,
                            title=f"{district} 추천 장소 {content_type_id}-{sequence}",
                            district=district,
                            latitude=37.50 + district_index * 0.02 + sequence * 0.002,
                            longitude=126.95 + content_type_id * 0.0005 + sequence * 0.002,
                        )
                    )
        db.add_all(locations)
        db.commit()

    def override_get_db() -> Iterator[Session]:
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.mark.parametrize(
    ("payload", "expected_place_count"),
    [
        (
            {
                "available_minutes": 120,
                "companion": "friends",
                "mood": "culture",
                "district": "종로구",
            },
            3,
        ),
        (
            {
                "available_minutes": 60,
                "companion": "solo",
                "mood": "shopping",
                "district": "강남구",
            },
            2,
        ),
        (
            {
                "available_minutes": 240,
                "companion": "couple",
                "mood": "healing",
                "district": "마포구",
            },
            4,
        ),
        (
            {
                "available_minutes": 120,
                "companion": "family",
                "mood": "activity",
                "district": "송파구",
            },
            3,
        ),
        (
            {"available_minutes": 30, "companion": "solo", "mood": "culture"},
            1,
        ),
        (
            {
                "available_minutes": 60,
                "companion": "couple",
                "mood": "night_view",
                "district": "종로구",
            },
            2,
        ),
        (
            {
                "available_minutes": 120,
                "companion": "family",
                "mood": "healing",
                "district": "강남구",
            },
            3,
        ),
        (
            {
                "available_minutes": 240,
                "companion": "friends",
                "mood": "shopping",
                "district": "마포구",
            },
            4,
        ),
    ],
)
def test_recommendation_rule_fallback_supports_representative_conditions(
    client: TestClient,
    payload: dict[str, object],
    expected_place_count: int,
) -> None:
    response = client.post("/api/recommend/situational", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["count"] == 3
    assert body["meta"]["fallback"] is True
    assert len(body["data"]["recommendations"]) == 3
    for course in body["data"]["recommendations"]:
        assert course["estimated_place_count"] == expected_place_count
        ids = [location["id"] for location in course["locations"]]
        assert len(ids) == len(set(ids)) == expected_place_count
        assert course["warnings"][0] == "정확한 이동시간과 최적 경로는 제공하지 않습니다."


def test_recommendation_uses_valid_openai_selection(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_openai_selection(
        candidates: list[Location],
        request: SituationalRecommendationRequest,
    ) -> AICourseSelection:
        del request
        pairs = ((0, 1), (1, 2), (2, 3))
        return AICourseSelection(
            recommendations=[
                AICourse(
                    title=f"AI 추천 코스 {index + 1}",
                    reason="후보 장소만 사용한 추천입니다.",
                    location_ids=[candidates[first].id, candidates[second].id],
                )
                for index, (first, second) in enumerate(pairs)
            ]
        )

    monkeypatch.setattr(
        recommendation_service,
        "_request_openai_recommendations",
        fake_openai_selection,
    )
    response = client.post(
        "/api/recommend/situational",
        json={"available_minutes": 60, "companion": "friends", "mood": "culture"},
    )

    assert response.status_code == 200
    assert response.json()["meta"]["fallback"] is False
    assert [course["title"] for course in response.json()["data"]["recommendations"]] == [
        "AI 추천 코스 1",
        "AI 추천 코스 2",
        "AI 추천 코스 3",
    ]


def test_recommendation_rejects_hallucinated_openai_ids(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_invalid_selection(
        candidates: list[Location],
        request: SituationalRecommendationRequest,
    ) -> AICourseSelection:
        del request
        return AICourseSelection(
            recommendations=[
                AICourse(
                    title=f"잘못된 코스 {index}",
                    reason="DB에 없는 ID를 포함합니다.",
                    location_ids=[candidates[index].id, 999999],
                )
                for index in range(3)
            ]
        )

    monkeypatch.setattr(
        recommendation_service,
        "_request_openai_recommendations",
        fake_invalid_selection,
    )
    response = client.post(
        "/api/recommend/situational",
        json={"available_minutes": 60, "companion": "friends", "mood": "culture"},
    )

    assert response.status_code == 200
    assert response.json()["meta"]["fallback"] is True
    returned_ids = {
        location["id"]
        for course in response.json()["data"]["recommendations"]
        for location in course["locations"]
    }
    assert 999999 not in returned_ids


@pytest.mark.parametrize(
    "payload",
    [
        {"available_minutes": 45, "companion": "friends", "mood": "culture"},
        {"available_minutes": 60, "companion": "team", "mood": "culture"},
        {"available_minutes": 60, "companion": "friends", "mood": "food"},
        {
            "available_minutes": 60,
            "companion": "friends",
            "mood": "culture",
            "district": "부산진구",
        },
        {
            "available_minutes": 60,
            "companion": "friends",
            "mood": "culture",
            "current_location": {"latitude": 100, "longitude": 126.98},
        },
    ],
)
def test_recommendation_rejects_invalid_conditions(
    client: TestClient,
    payload: dict[str, object],
) -> None:
    response = client.post("/api/recommend/situational", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_RECOMMENDATION_CONDITION"


def test_recommendation_returns_empty_result_without_candidates() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        response = recommendation_service.recommend_situational(
            db,
            SituationalRecommendationRequest(
                available_minutes=60,
                companion="solo",
                mood="culture",
            ),
        )

    assert response.meta.count == 0
    assert response.meta.fallback is True
    assert response.data.recommendations == []


def test_recommendation_openapi_has_korean_description(client: TestClient) -> None:
    response = client.get("/api/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/api/recommend/situational"]["post"]
    assert operation["tags"] == ["상황형 추천"]
    assert operation["summary"] == "상황형 서울 여행코스 추천"
    assert "규칙 기반 코스로 자동 전환" in operation["description"]


def _location(**overrides: object) -> Location:
    defaults: dict[str, object] = {
        "address": "서울특별시 테스트구 테스트로 1",
        "image_url": "https://example.com/location.jpg",
        "thumbnail_url": None,
        "telephone": None,
        "copyright_code": "Type1",
        "category_code_1": None,
        "category_code_2": None,
        "category_code_3": None,
        "classification_code_1": None,
        "classification_code_2": None,
        "classification_code_3": None,
        "source_created_at": datetime(2023, 1, 1),
        "source_modified_at": datetime(2026, 1, 1),
        "raw_json": "{}",
    }
    defaults.update(overrides)
    return Location(**defaults)
