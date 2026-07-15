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
from app.repositories.location import find_recommendation_candidates
from app.schemas.recommendation import (
    AICourse,
    AICourseSelection,
    SituationalRecommendationRequest,
)
from app.services import recommendation as recommendation_service

DISTRICTS = ("종로구", "강남구", "마포구", "송파구")
CONTENT_TYPE_IDS = (12, 14, 15, 25, 28, 38)


@pytest.fixture(autouse=True)
def disable_external_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        recommendation_service,
        "_request_openai_recommendations",
        lambda course_options, request: None,
    )


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
    "payload",
    [
        {
            "recommendation_mode": "district",
            "available_minutes": 120,
            "companion": "friends",
            "mood": "culture",
            "district": "종로구",
        },
        {
            "recommendation_mode": "district",
            "available_minutes": 60,
            "companion": "solo",
            "mood": "shopping",
            "district": "강남구",
        },
        {
            "recommendation_mode": "district",
            "available_minutes": 240,
            "companion": "couple",
            "mood": "healing",
            "district": "마포구",
        },
        {
            "recommendation_mode": "district",
            "available_minutes": 120,
            "companion": "family",
            "mood": "activity",
            "district": "송파구",
        },
        {
            "recommendation_mode": "nearby",
            "available_minutes": 30,
            "companion": "solo",
            "mood": "culture",
            "current_location": {"latitude": 37.50, "longitude": 126.956},
        },
        {
            "recommendation_mode": "district",
            "available_minutes": 60,
            "companion": "couple",
            "mood": "night_view",
            "district": "종로구",
        },
        {
            "recommendation_mode": "district",
            "available_minutes": 120,
            "companion": "family",
            "mood": "healing",
            "district": "강남구",
        },
        {
            "recommendation_mode": "district",
            "available_minutes": 240,
            "companion": "friends",
            "mood": "shopping",
            "district": "마포구",
        },
    ],
)
def test_recommendation_rule_fallback_supports_representative_conditions(
    client: TestClient,
    payload: dict[str, object],
) -> None:
    response = client.post("/api/recommend/situational", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert 1 <= body["meta"]["count"] <= 3
    assert body["meta"]["fallback"] is True
    assert len(body["data"]["recommendations"]) == body["meta"]["count"]
    applied = body["data"]["applied_conditions"]
    assert applied["recommendation_mode"] == payload["recommendation_mode"]
    if payload["recommendation_mode"] == "nearby":
        assert applied["district"] is None
        assert applied["current_location"] == payload["current_location"]
    else:
        assert applied["district"] == payload["district"]
        assert applied["current_location"] is None
    all_ids: list[int] = []
    for course in body["data"]["recommendations"]:
        assert course["estimated_duration_minutes"] <= payload["available_minutes"]
        assert course["estimated_duration_minutes"] == (
            sum(location["estimated_visit_minutes"] for location in course["locations"])
            + course["estimated_travel_minutes"]
        )
        ids = [location["id"] for location in course["locations"]]
        assert len(ids) == len(set(ids)) == course["estimated_place_count"]
        assert all(location["experience_type"] for location in course["locations"])
        assert course["warnings"][0].startswith("이동시간과 거리는 직선거리")
        all_ids.extend(ids)
    assert len(all_ids) == len(set(all_ids))


def test_recommendation_uses_valid_openai_selection(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_openai_selection(
        course_options: list[recommendation_service.CourseOption],
        request: SituationalRecommendationRequest,
    ) -> AICourseSelection:
        del request
        selected = recommendation_service._select_fallback_options(course_options)
        return AICourseSelection(
            recommendations=[
                AICourse(
                    title=f"AI 추천 코스 {index + 1}",
                    reason="검증된 후보 코스만 사용한 추천입니다.",
                    candidate_course_id=option.id,
                )
                for index, option in enumerate(selected)
            ]
        )

    monkeypatch.setattr(
        recommendation_service,
        "_request_openai_recommendations",
        fake_openai_selection,
    )
    response = client.post(
        "/api/recommend/situational",
        json={
            "recommendation_mode": "district",
            "available_minutes": 60,
            "companion": "friends",
            "mood": "culture",
            "district": "종로구",
        },
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
        course_options: list[recommendation_service.CourseOption],
        request: SituationalRecommendationRequest,
    ) -> AICourseSelection:
        del course_options
        del request
        return AICourseSelection(
            recommendations=[
                AICourse(
                    title=f"잘못된 코스 {index}",
                    reason="서버가 제공하지 않은 코스 ID를 포함합니다.",
                    candidate_course_id=f"candidate-{999997 + index}",
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
        json={
            "recommendation_mode": "district",
            "available_minutes": 60,
            "companion": "friends",
            "mood": "culture",
            "district": "종로구",
        },
    )

    assert response.status_code == 200
    assert response.json()["meta"]["fallback"] is True
    returned_ids = {
        location["id"]
        for course in response.json()["data"]["recommendations"]
        for location in course["locations"]
    }
    assert 999999 not in returned_ids


def test_culture_courses_balance_museum_time_diversity_and_distance() -> None:
    request = SituationalRecommendationRequest(
        recommendation_mode="nearby",
        available_minutes=120,
        companion="friends",
        mood="culture",
        current_location={"latitude": 37.575, "longitude": 126.98},
    )
    definitions = [
        ("신문박물관", 14),
        ("역사박물관", 14),
        ("현대미술관", 14),
        ("미디어아카이브", 14),
        ("한옥문화거리", 12),
        ("전통문화유적", 12),
        ("궁궐역사터", 12),
        ("종묘문화재", 12),
        ("도심산책길", 12),
        ("문화광장", 12),
        ("전망공원", 12),
        ("숲둘레길", 12),
    ]
    candidates: list[recommendation_service.ScoredCandidate] = []
    for index, (title, content_type_id) in enumerate(definitions, start=1):
        location = _location(
            id=index,
            source_content_id=f"quality-{index}",
            content_type_id=content_type_id,
            title=title,
            district="종로구",
            latitude=37.575 + index * 0.0002,
            longitude=126.98 + index * 0.0002,
        )
        experience_type = recommendation_service._classify_experience(location)
        candidates.append(
            recommendation_service.ScoredCandidate(
                location=location,
                score=100 - index,
                experience_type=experience_type,
                visit_minutes=recommendation_service.EXPERIENCE_VISIT_MINUTES[
                    experience_type
                ],
            )
        )

    options = recommendation_service._build_course_options(
        candidates,
        request,
        require_diversity=True,
    )
    selected = recommendation_service._select_fallback_options(options)

    assert len(selected) == 3
    all_ids: list[int] = []
    for option in selected:
        assert option.estimated_duration_minutes <= 120
        assert option.experience_types.count("museum_art") <= 1
        assert len(set(option.experience_types)) >= 2
        all_ids.extend(option.location_ids)
    assert len(all_ids) == len(set(all_ids))


def test_shopping_and_activity_candidates_exclude_museum_experience() -> None:
    assert "museum_art" not in recommendation_service.MOOD_EXPERIENCE_TYPES["shopping"]
    assert "museum_art" not in recommendation_service.MOOD_EXPERIENCE_TYPES["activity"]


def test_nearby_candidate_query_prioritizes_current_location() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                _location(
                    source_content_id="nearby-old",
                    content_type_id=12,
                    title="현재 위치 근처",
                    district="종로구",
                    latitude=37.5751,
                    longitude=126.9801,
                    source_modified_at=datetime(2023, 1, 1),
                ),
                _location(
                    source_content_id="distant-new",
                    content_type_id=12,
                    title="현재 위치에서 먼 장소",
                    district="강남구",
                    latitude=37.50,
                    longitude=127.10,
                    source_modified_at=datetime(2026, 1, 1),
                ),
            ]
        )
        db.commit()

        locations = find_recommendation_candidates(
            db,
            content_type_ids={12},
            district=None,
            latitude=37.575,
            longitude=126.98,
            limit=1,
        )

    assert [location.title for location in locations] == ["현재 위치 근처"]


def test_nearby_mode_includes_access_travel_but_district_mode_does_not() -> None:
    location = _location(
        id=1,
        source_content_id="travel-mode",
        content_type_id=12,
        title="이동시간 비교 장소",
        district="종로구",
        latitude=37.585,
        longitude=126.99,
    )
    candidate = recommendation_service.ScoredCandidate(
        location=location,
        score=50,
        experience_type="general_attraction",
        visit_minutes=30,
    )
    nearby_request = SituationalRecommendationRequest(
        recommendation_mode="nearby",
        available_minutes=60,
        companion="solo",
        mood="healing",
        current_location={"latitude": 37.575, "longitude": 126.98},
    )
    district_request = SituationalRecommendationRequest(
        recommendation_mode="district",
        available_minutes=60,
        companion="solo",
        mood="healing",
        district="종로구",
    )

    nearby_travel, _ = recommendation_service._estimate_travel(
        (candidate,), nearby_request
    )
    district_travel, _ = recommendation_service._estimate_travel(
        (candidate,), district_request
    )

    assert nearby_travel > 0
    assert district_travel == 0


@pytest.mark.parametrize(
    "payload",
    [
        {
            "recommendation_mode": "district",
            "available_minutes": 45,
            "companion": "friends",
            "mood": "culture",
            "district": "종로구",
        },
        {
            "recommendation_mode": "district",
            "available_minutes": 60,
            "companion": "team",
            "mood": "culture",
            "district": "종로구",
        },
        {
            "recommendation_mode": "district",
            "available_minutes": 60,
            "companion": "friends",
            "mood": "food",
            "district": "종로구",
        },
        {
            "recommendation_mode": "district",
            "available_minutes": 60,
            "companion": "friends",
            "mood": "culture",
            "district": "부산진구",
        },
        {
            "recommendation_mode": "nearby",
            "available_minutes": 60,
            "companion": "friends",
            "mood": "culture",
            "current_location": {"latitude": 100, "longitude": 126.98},
        },
        {
            "recommendation_mode": "nearby",
            "available_minutes": 60,
            "companion": "friends",
            "mood": "culture",
        },
        {
            "recommendation_mode": "nearby",
            "available_minutes": 60,
            "companion": "friends",
            "mood": "culture",
            "district": "종로구",
            "current_location": {"latitude": 37.575, "longitude": 126.98},
        },
        {
            "recommendation_mode": "district",
            "available_minutes": 60,
            "companion": "friends",
            "mood": "culture",
        },
        {
            "recommendation_mode": "district",
            "available_minutes": 60,
            "companion": "friends",
            "mood": "culture",
            "district": "종로구",
            "current_location": {"latitude": 37.575, "longitude": 126.98},
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
                recommendation_mode="district",
                available_minutes=60,
                companion="solo",
                mood="culture",
                district="종로구",
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
    assert "nearby 모드는 현재 위치 주변" in operation["description"]
    assert "서버가 선택한 검증 코스로 자동 전환" in operation["description"]


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
