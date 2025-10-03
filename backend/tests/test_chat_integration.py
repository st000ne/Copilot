import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="No OPENAI_API_KEY provided")
def test_integration_chat():
    r = client.post("/chat", json={"messages":[{"role":"user","content":"Hello from test"}]})
    assert r.status_code == 200
    j = r.json()
    assert "reply" in j and isinstance(j["reply"], dict)