from pathlib import Path

from config import get_settings


def test_health_reports_llm_unconfigured(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["database"] is True
    assert body["llm_configured"] is False


def test_health_reports_llm_configured(client, llm_enabled):
    assert client.get("/api/health").json()["llm_configured"] is True


def test_llm_ping_without_key_returns_503(client, auth_headers):
    assert client.get("/api/llm-ping", headers=auth_headers).status_code == 503


def test_llm_ping_with_mocked_gemini(client, auth_headers, llm_enabled, monkeypatch):
    class FakeModels:
        def generate_content(self, **kwargs):
            return type("Resp", (), {"text": "pong"})()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr("routers.system.genai.Client", lambda: FakeClient())
    assert client.get("/api/llm-ping", headers=auth_headers).json() == {"reply": "pong"}


def test_unknown_api_route_is_json_404(client):
    assert client.get("/api/does-not-exist").status_code == 404


def test_frontend_fallback_without_build(client):
    body = client.get("/").json()
    assert body["status"] == "running"


def test_frontend_serves_index_for_client_routes(client):
    dist = Path(get_settings().frontend_dist)
    (dist / "index.html").write_text("<html>app</html>")
    (dist / "asset.js").write_text("console.log(1)")
    try:
        assert client.get("/submissions/5").text == "<html>app</html>"
        assert client.get("/asset.js").text == "console.log(1)"
        # Path traversal must not escape the dist directory.
        assert client.get("/..%2F..%2Fetc%2Fpasswd").text == "<html>app</html>"
    finally:
        (dist / "index.html").unlink()
        (dist / "asset.js").unlink()
