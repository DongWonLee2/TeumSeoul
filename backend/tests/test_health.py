from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def override_get_db():
    with Session(test_engine) as session:
        yield session


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app, raise_server_exceptions=False)


def test_health_check() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert body["data"]["database"] == "connected"
    assert body["data"]["location_count"] == 0
    assert "timestamp" in body["data"]
    assert "meta" not in body


def test_not_found_uses_common_error_shape() -> None:
    response = client.get("/api/not-found")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found", "code": "RESOURCE_NOT_FOUND"}
