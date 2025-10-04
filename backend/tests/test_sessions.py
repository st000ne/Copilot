from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_create_session():
    r = client.post("/session/new")
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data

def test_missing_session_rejected():
    r = client.post("/chat", json={"messages": [{"role": "user", "content": "Hello"}]})
    assert r.status_code == 400
