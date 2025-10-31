from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body.get("message") == "API is operational"


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


