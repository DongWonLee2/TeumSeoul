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


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                _location(
                    source_content_id="map-1",
                    content_type_id=12,
                    title="서울숲",
                    district="성동구",
                    latitude=37.5430,
                    longitude=127.0418,
                ),
                _location(
                    source_content_id="map-2",
                    content_type_id=14,
                    title="성수 문화공간",
                    district="성동구",
                    latitude=37.5480,
                    longitude=127.0418,
                ),
                _location(
                    source_content_id="map-3",
                    content_type_id=38,
                    title="강남 쇼핑센터",
                    district="강남구",
                    latitude=37.4979,
                    longitude=127.0276,
                ),
                _location(
                    source_content_id="map-4",
                    content_type_id=25,
                    title="좌표 없는 여행코스",
                    district=None,
                    latitude=None,
                    longitude=None,
                ),
            ]
        )
        db.commit()

    def override_get_db() -> Iterator[Session]:
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_map_locations_filters_bounds_and_content_types(client: TestClient) -> None:
    response = client.get(
        "/api/map/locations",
        params={
            "south": 37.50,
            "west": 126.95,
            "north": 37.58,
            "east": 127.08,
            "content_type_ids": "12,14",
            "limit": 300,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert [location["title"] for location in body["data"]] == ["서울숲", "성수 문화공간"]
    assert body["data"][0]["content_type"] == "관광지"
    assert set(body["data"][0]) == {
        "id",
        "title",
        "content_type_id",
        "content_type",
        "district",
        "latitude",
        "longitude",
        "thumbnail_url",
    }
    assert body["meta"] == {"count": 2, "limit": 300, "truncated": False}


def test_map_locations_reports_truncated_result(client: TestClient) -> None:
    response = client.get(
        "/api/map/locations",
        params={
            "south": 37.49,
            "west": 126.95,
            "north": 37.58,
            "east": 127.08,
            "limit": 1,
        },
    )

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
    assert response.json()["meta"] == {"count": 1, "limit": 1, "truncated": True}


@pytest.mark.parametrize(
    ("params", "expected_status", "expected_code"),
    [
        (
            {"south": 37.6, "west": 126.9, "north": 37.5, "east": 127.1},
            400,
            "INVALID_BOUNDS",
        ),
        (
            {"south": -91, "west": 126.9, "north": 37.5, "east": 127.1},
            400,
            "INVALID_BOUNDS",
        ),
        (
            {
                "south": 37.5,
                "west": 126.9,
                "north": 37.6,
                "east": 127.1,
                "content_type_ids": "12,999",
            },
            422,
            "INVALID_QUERY_PARAMETER",
        ),
        (
            {
                "south": 37.5,
                "west": 126.9,
                "north": 37.6,
                "east": 127.1,
                "content_type_ids": "12,",
            },
            422,
            "INVALID_QUERY_PARAMETER",
        ),
        (
            {"south": 37.5, "west": 126.9, "north": 37.6, "east": 127.1, "limit": 301},
            422,
            "INVALID_QUERY_PARAMETER",
        ),
    ],
)
def test_map_locations_rejects_invalid_parameters(
    client: TestClient,
    params: dict[str, object],
    expected_status: int,
    expected_code: str,
) -> None:
    response = client.get("/api/map/locations", params=params)

    assert response.status_code == expected_status
    assert response.json()["code"] == expected_code


def test_metadata_returns_shared_options_and_actual_districts(client: TestClient) -> None:
    response = client.get("/api/meta")

    assert response.status_code == 200
    data = response.json()["data"]
    assert [content_type["id"] for content_type in data["content_types"]] == [
        12,
        14,
        15,
        25,
        28,
        32,
        38,
    ]
    assert data["districts"] == ["강남구", "성동구"]
    assert data["post_categories"] == ["현장 제보", "방문 후기", "질문", "추천"]
    assert data["recommendation_options"] == {
        "available_minutes": [30, 60, 120, 240],
        "companions": ["solo", "couple", "friends", "family"],
        "moods": ["healing", "culture", "activity", "night_view", "shopping"],
    }


def test_map_and_meta_openapi_has_korean_descriptions(client: TestClient) -> None:
    response = client.get("/api/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    map_operation = paths["/api/map/locations"]["get"]
    meta_operation = paths["/api/meta"]["get"]
    assert map_operation["tags"] == ["지도"]
    assert map_operation["summary"] == "지도 영역 장소 조회"
    assert meta_operation["tags"] == ["메타데이터"]
    assert meta_operation["summary"] == "필터 및 추천 옵션 조회"


def _location(**overrides: object) -> Location:
    defaults: dict[str, object] = {
        "address": None,
        "image_url": None,
        "thumbnail_url": None,
        "telephone": None,
        "copyright_code": None,
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
