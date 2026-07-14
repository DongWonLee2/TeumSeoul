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
                    source_content_id="1",
                    content_type_id=12,
                    title="서울숲",
                    address="서울특별시 성동구 뚝섬로 273",
                    district="성동구",
                    latitude=37.5430,
                    longitude=127.0418,
                    image_url="https://example.com/seoul-forest.jpg",
                    source_modified_at=datetime(2026, 6, 19, 9, 32, 9),
                ),
                _location(
                    source_content_id="2",
                    content_type_id=14,
                    title="성수 문화공간",
                    address="서울특별시 성동구 성수동1가",
                    district="성동구",
                    latitude=37.5480,
                    longitude=127.0418,
                    image_url=None,
                    source_modified_at=datetime(2025, 1, 1),
                ),
                _location(
                    source_content_id="3",
                    content_type_id=38,
                    title="강남 쇼핑센터",
                    address="서울특별시 강남구 테헤란로 1",
                    district="강남구",
                    latitude=37.4979,
                    longitude=127.0276,
                    image_url="https://example.com/shopping.jpg",
                    source_modified_at=datetime(2024, 1, 1),
                ),
                _location(
                    source_content_id="4",
                    content_type_id=25,
                    title="서울 대표 여행코스",
                    address=None,
                    district=None,
                    latitude=None,
                    longitude=None,
                    image_url=None,
                    source_modified_at=datetime(2023, 1, 1),
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


def test_location_list_supports_filters_and_pagination(client: TestClient) -> None:
    response = client.get(
        "/api/locations",
        params={
            "q": "서울숲",
            "content_type_id": 12,
            "district": "성동구",
            "page": 1,
            "size": 1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert [location["title"] for location in body["data"]] == ["서울숲"]
    assert body["data"][0]["content_type"] == "관광지"
    assert body["data"][0]["warnings"] == []
    assert body["meta"] == {
        "page": 1,
        "size": 1,
        "total_items": 1,
        "total_pages": 1,
    }


def test_location_list_supports_image_year_and_title_sort(client: TestClient) -> None:
    response = client.get(
        "/api/locations",
        params={"has_image": "false", "modified_year": 2025, "sort": "title"},
    )

    assert response.status_code == 200
    assert [location["title"] for location in response.json()["data"]] == ["성수 문화공간"]
    assert response.json()["data"][0]["warnings"] == ["대표 이미지 없음"]


def test_location_detail_contains_warnings_and_nearby_locations(client: TestClient) -> None:
    response = client.get("/api/locations/1")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "서울숲"
    assert data["related_post_count"] == 0
    assert data["related_posts"] == []
    assert data["warnings"] == [
        "운영시간은 제공 데이터에 없어 방문 전 확인이 필요합니다."
    ]
    assert [nearby["id"] for nearby in data["nearby_locations"]] == [2]
    assert data["nearby_locations"][0]["distance_km"] == pytest.approx(0.56, abs=0.01)


def test_location_detail_reports_missing_source_data(client: TestClient) -> None:
    response = client.get("/api/locations/4")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["nearby_locations"] == []
    assert data["warnings"] == [
        "주소 정보 없음",
        "대표 이미지 없음",
        "정확한 위치 정보 없음",
        "대표 위치이며 전체 이동 경로가 아님",
        "운영시간은 제공 데이터에 없어 방문 전 확인이 필요합니다.",
    ]


def test_location_not_found_uses_domain_error_code(client: TestClient) -> None:
    response = client.get("/api/locations/999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "장소를 찾을 수 없습니다.",
        "code": "LOCATION_NOT_FOUND",
    }


@pytest.mark.parametrize(
    "query_string",
    ["content_type_id=999", "size=101", "page=0", "sort=unknown"],
)
def test_location_list_rejects_invalid_query(
    client: TestClient,
    query_string: str,
) -> None:
    response = client.get(f"/api/locations?{query_string}")

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_QUERY_PARAMETER"


def _location(**overrides: object) -> Location:
    defaults: dict[str, object] = {
        "thumbnail_url": None,
        "telephone": None,
        "copyright_code": None,
        "category_code_1": "A01",
        "category_code_2": "A0101",
        "category_code_3": "A01010100",
        "classification_code_1": None,
        "classification_code_2": None,
        "classification_code_3": None,
        "source_created_at": datetime(2023, 1, 1),
        "raw_json": "{}",
    }
    defaults.update(overrides)
    return Location(**defaults)
