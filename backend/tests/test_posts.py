from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.location import Location
from app.models.mixins import utc_now
from app.models.post import Post
from app.schemas.post import PostCreate
from app.services.post import create_post


@pytest.fixture
def post_api() -> Generator[tuple[TestClient, Session], None, None]:
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


def add_location(db: Session, *, title: str = "서울숲", district: str = "성동구") -> Location:
    now = utc_now()
    location = Location(
        source_content_id=f"test-{title}",
        content_type_id=12,
        title=title,
        address=f"서울특별시 {district}",
        district=district,
        latitude=37.5,
        longitude=127.0,
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


def create_payload(location_id: int | None = None) -> dict[str, object]:
    return {
        "location_id": location_id,
        "category": "현장 제보",
        "status_tag": "혼잡",
        "title": "<b>주말 혼잡 정보</b>",
        "content": "<script>alert('xss')</script> 산책로가 혼잡했습니다.",
        "password": "1234",
        "visited_at": "2026-07-13",
    }


def test_post_crud_search_views_and_password_is_never_exposed(post_api) -> None:
    client, db = post_api
    location = add_location(db)

    created = client.post("/api/posts", json=create_payload(location.id))
    assert created.status_code == 201
    created_body = created.json()
    post_id = created_body["data"]["id"]
    assert "meta" not in created_body
    assert "password" not in created.text
    assert created_body["data"]["title"] == "&lt;b&gt;주말 혼잡 정보&lt;/b&gt;"
    assert "&lt;script&gt;" in created_body["data"]["content"]
    assert created_body["data"]["location"] == {"id": location.id, "title": "서울숲"}

    listed = client.get("/api/posts", params={"q": "서울숲", "district": "성동구"})
    assert listed.status_code == 200
    assert listed.json()["meta"] == {
        "page": 1,
        "size": 20,
        "total_items": 1,
        "total_pages": 1,
    }
    assert listed.json()["data"][0]["view_count"] == 0
    assert "password" not in listed.text

    detail = client.get(f"/api/posts/{post_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["view_count"] == 1
    assert detail.json()["data"]["location"]["address"] == "서울특별시 성동구"
    assert client.get(f"/api/posts/{post_id}").json()["data"]["view_count"] == 2

    free_post_payload = {
        **create_payload(None),
        "category": "질문",
        "status_tag": None,
        "title": "장소 없는 자유 질문",
        "content": "서울 나들이 장소가 궁금합니다.",
    }
    free_post = client.post("/api/posts", json=free_post_payload)
    assert free_post.status_code == 201
    assert free_post.json()["data"]["location"] is None
    views_sorted = client.get(
        "/api/posts", params={"sort": "views", "category": "현장 제보", "size": 1}
    )
    assert views_sorted.status_code == 200
    assert views_sorted.json()["data"][0]["id"] == post_id
    assert views_sorted.json()["meta"]["total_items"] == 1

    denied = client.put(
        f"/api/posts/{post_id}",
        json={**create_payload(location.id), "password": "wrong"},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "INVALID_POST_PASSWORD"
    assert "wrong" not in denied.text

    updated_payload = {
        **create_payload(None),
        "password": "1234",
        "category": "방문 후기",
        "status_tag": "여유",
        "title": "평일 오전 후기",
        "content": "평일 오전에는 비교적 여유로웠습니다.",
    }
    updated = client.put(f"/api/posts/{post_id}", json=updated_payload)
    assert updated.status_code == 200
    assert updated.json()["data"]["location"] is None
    assert updated.json()["data"]["view_count"] == 2
    assert "password" not in updated.text

    denied_delete = client.request(
        "DELETE", f"/api/posts/{post_id}", json={"password": "wrong"}
    )
    assert denied_delete.status_code == 403
    deleted = client.request(
        "DELETE", f"/api/posts/{post_id}", json={"password": "1234"}
    )
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert db.scalar(select(Post).where(Post.id == post_id)) is None
    assert client.get(f"/api/posts/{post_id}").json()["code"] == "POST_NOT_FOUND"


def test_post_validation_and_missing_resources(post_api) -> None:
    client, _ = post_api

    missing_location = client.post("/api/posts", json=create_payload(9999))
    assert missing_location.status_code == 404
    assert missing_location.json()["code"] == "LOCATION_NOT_FOUND"

    invalid = client.post(
        "/api/posts",
        json={**create_payload(), "title": "x", "category": "잘못된 값"},
    )
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "INVALID_POST_INPUT"

    invalid_filter = client.get("/api/posts", params={"status_tag": "잘못된 값"})
    assert invalid_filter.status_code == 422
    assert invalid_filter.json()["code"] == "INVALID_QUERY_PARAMETER"

    missing_post = client.put("/api/posts/9999", json=create_payload())
    assert missing_post.status_code == 404
    assert missing_post.json()["code"] == "POST_NOT_FOUND"


def test_post_schema_matches_erd_and_location_delete_sets_null() -> None:
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record) -> None:
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    schema = inspect(engine)
    columns = {column["name"]: column for column in schema.get_columns("posts")}
    assert set(columns) == {
        "id",
        "location_id",
        "category",
        "status_tag",
        "title",
        "content",
        "password",
        "visited_at",
        "view_count",
        "created_at",
        "updated_at",
    }
    assert columns["location_id"]["nullable"] is True
    assert columns["status_tag"]["nullable"] is True
    assert columns["visited_at"]["nullable"] is True
    assert str(columns["view_count"]["default"]).strip("'\"") == "0"
    index_names = {index["name"] for index in schema.get_indexes("posts")}
    assert {
        "ix_posts_created_at",
        "ix_posts_category_status",
        "ix_posts_location_id",
    } <= index_names
    foreign_key = schema.get_foreign_keys("posts")[0]
    assert foreign_key["referred_table"] == "locations"
    assert foreign_key["options"]["ondelete"] == "SET NULL"

    with Session(engine, expire_on_commit=False) as db:
        location = add_location(db, title="삭제 관계 검증 장소")
        post = Post(
            location_id=location.id,
            category="질문",
            title="관계 검증 게시글",
            content="장소 삭제 후 자유글로 유지되어야 합니다.",
            password="1234",
        )
        db.add(post)
        db.commit()
        post_id = post.id
        db.delete(location)
        db.commit()
        db.expire_all()
        assert db.get(Post, post_id).location_id is None


def test_post_only_reads_public_location_columns() -> None:
    """BE2는 Location ORM 전체가 아닌 교차 도메인 공개 컬럼만 조회한다."""
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE locations (
                    id INTEGER PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    address TEXT,
                    latitude REAL,
                    longitude REAL
                )
                """
            )
        )
        connection.execute(
            text(
                "INSERT INTO locations (id, title, address, latitude, longitude) "
                "VALUES (1, '서울숲', '서울특별시 성동구', 37.5, 127.0)"
            )
        )
    Post.__table__.create(engine)

    payload = PostCreate(
        location_id=1,
        category="질문",
        title="공개 컬럼 조회 검증",
        content="Location 내부 스키마에 결합되지 않아야 합니다.",
        password="1234",
    )
    with Session(engine, expire_on_commit=False) as db:
        result = create_post(db, payload)
        assert result.location is not None
        assert result.location.id == 1
        assert result.location.title == "서울숲"
