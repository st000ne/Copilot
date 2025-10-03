from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_too_long_message_rejected():
    long_text = "x" * 25000
    r = client.post("/chat", json={"messages":[{"role":"user","content": long_text}]})
    assert r.status_code == 400
