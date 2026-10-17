from judge import Judgment
from tests.helpers import register


def _mock_judging(monkeypatch, claims=("Claim A.", "Claim B."), judge=None):
    monkeypatch.setattr(
        "routers.submissions.retrieve_relevant_chunks", lambda sid, claim, k=5: ["evidence"]
    )
    monkeypatch.setattr("routers.submissions.extract_claims", lambda summary: list(claims))
    monkeypatch.setattr(
        "routers.submissions.judge_claim",
        judge or (lambda claim, evidence: Judgment(verdict="SUPPORTED", reason="ok")),
    )


def test_create_submission_chunks_and_stores(make_submission, mock_indexing):
    body = make_submission(source_document="Some source text.", summary="A summary.")

    assert body["source_document"] == "Some source text."
    assert body["chunk_count"] == 2
    assert mock_indexing[body["id"]] == ["chunk one", "chunk two"]


def test_create_submission_defaults_title_from_summary(make_submission):
    body = make_submission(summary="First line of summary.\nSecond line.")
    assert body["title"] == "First line of summary."


def test_create_submission_rejects_empty_document(client, auth_headers, mock_indexing):
    resp = client.post(
        "/api/submissions", json={"source_document": "", "summary": "x"}, headers=auth_headers
    )
    assert resp.status_code == 422


def test_create_submission_requires_auth(client, mock_indexing):
    resp = client.post("/api/submissions", json={"source_document": "d", "summary": "s"})
    assert resp.status_code == 401


def test_indexing_failure_rolls_back_submission(client, auth_headers, monkeypatch):
    def broken_store(submission_id, chunks):
        raise RuntimeError("model download failed")

    monkeypatch.setattr("routers.submissions.chunk_text", lambda text, **kw: ["c"])
    monkeypatch.setattr("routers.submissions.store_chunks", broken_store)

    resp = client.post(
        "/api/submissions", json={"source_document": "d", "summary": "s"}, headers=auth_headers
    )
    assert resp.status_code == 503
    assert client.get("/api/submissions", headers=auth_headers).json() == []


def test_list_submissions_returns_created_rows(client, auth_headers, make_submission):
    make_submission(title="first")
    make_submission(title="second")

    resp = client.get("/api/submissions", headers=auth_headers)

    assert resp.status_code == 200
    rows = resp.json()
    assert [r["title"] for r in rows] == ["second", "first"]  # newest first
    assert all(r["check_count"] == 0 for r in rows)


def test_users_only_see_their_own_submissions(client, auth_headers, make_submission):
    mine = make_submission(title="mine")
    bob = {"Authorization": f"Bearer {register(client, 'bob@example.com')['access_token']}"}

    assert client.get("/api/submissions", headers=bob).json() == []
    assert client.get(f"/api/submissions/{mine['id']}", headers=bob).status_code == 404
    assert client.delete(f"/api/submissions/{mine['id']}", headers=bob).status_code == 404


def test_delete_submission_removes_row_and_chunks(
    client, auth_headers, make_submission, mock_indexing
):
    sub = make_submission()

    resp = client.delete(f"/api/submissions/{sub['id']}", headers=auth_headers)

    assert resp.status_code == 204
    assert sub["id"] not in mock_indexing
    assert client.get(f"/api/submissions/{sub['id']}", headers=auth_headers).status_code == 404


def test_check_claim_returns_judgment(
    client, auth_headers, make_submission, llm_enabled, monkeypatch
):
    _mock_judging(monkeypatch)
    sub = make_submission()

    resp = client.post(
        f"/api/submissions/{sub['id']}/check", json={"claim": "A claim."}, headers=auth_headers
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "SUPPORTED"
    assert body["evidence"] == ["evidence"]


def test_check_claim_missing_submission_returns_404(client, auth_headers, llm_enabled):
    resp = client.post("/api/submissions/999/check", json={"claim": "x"}, headers=auth_headers)
    assert resp.status_code == 404


def test_check_summary_returns_one_result_per_claim(
    client, auth_headers, make_submission, llm_enabled, monkeypatch
):
    _mock_judging(monkeypatch)
    sub = make_submission()

    resp = client.post(f"/api/submissions/{sub['id']}/check-summary", headers=auth_headers)

    assert resp.status_code == 201
    run = resp.json()
    assert [r["claim"] for r in run["results"]] == ["Claim A.", "Claim B."]
    assert run["verdict_counts"]["SUPPORTED"] == 2


def test_check_summary_is_persisted_in_history(
    client, auth_headers, make_submission, llm_enabled, monkeypatch
):
    _mock_judging(monkeypatch)
    sub = make_submission()
    client.post(f"/api/submissions/{sub['id']}/check-summary", headers=auth_headers)
    client.post(f"/api/submissions/{sub['id']}/check-summary", headers=auth_headers)

    detail = client.get(f"/api/submissions/{sub['id']}", headers=auth_headers).json()
    listing = client.get("/api/submissions", headers=auth_headers).json()

    assert len(detail["check_runs"]) == 2
    assert detail["check_runs"][0]["id"] > detail["check_runs"][1]["id"]  # newest first
    assert detail["check_runs"][0]["results"][0]["evidence"] == ["evidence"]
    assert listing[0]["check_count"] == 2


def test_check_summary_missing_submission_returns_404(client, auth_headers, llm_enabled):
    resp = client.post("/api/submissions/999999/check-summary", headers=auth_headers)
    assert resp.status_code == 404


def test_check_summary_partial_failure_does_not_lose_other_results(
    client, auth_headers, make_submission, llm_enabled, monkeypatch
):
    def flaky_judge_claim(claim, evidence):
        if claim == "Claim B.":
            raise RuntimeError("simulated transient failure")
        return Judgment(verdict="SUPPORTED", reason="ok")

    _mock_judging(monkeypatch, claims=("Claim A.", "Claim B.", "Claim C."), judge=flaky_judge_claim)
    sub = make_submission()

    resp = client.post(f"/api/submissions/{sub['id']}/check-summary", headers=auth_headers)

    assert resp.status_code == 201
    by_claim = {r["claim"]: r for r in resp.json()["results"]}
    assert by_claim["Claim A."]["verdict"] == "SUPPORTED"
    assert by_claim["Claim B."]["verdict"] == "ERROR"
    assert by_claim["Claim C."]["verdict"] == "SUPPORTED"


def test_check_summary_claim_extraction_failure_returns_502(
    client, auth_headers, make_submission, llm_enabled, monkeypatch
):
    def broken_extract(summary):
        raise RuntimeError("quota exceeded")

    monkeypatch.setattr("routers.submissions.extract_claims", broken_extract)
    sub = make_submission()

    resp = client.post(f"/api/submissions/{sub['id']}/check-summary", headers=auth_headers)
    assert resp.status_code == 502


def test_check_summary_caps_number_of_claims(
    client, auth_headers, make_submission, llm_enabled, monkeypatch
):
    from config import get_settings

    monkeypatch.setattr(get_settings(), "max_claims_per_check", 3)
    _mock_judging(monkeypatch, claims=[f"Claim {i}." for i in range(10)])
    sub = make_submission()

    resp = client.post(f"/api/submissions/{sub['id']}/check-summary", headers=auth_headers)
    assert len(resp.json()["results"]) == 3


def test_checks_degrade_gracefully_without_gemini_key(
    client, auth_headers, make_submission, monkeypatch
):
    def must_not_be_called(*args, **kwargs):
        raise AssertionError("Gemini should not be called without a key")

    monkeypatch.setattr("routers.submissions.extract_claims", must_not_be_called)
    sub = make_submission()

    summary_resp = client.post(f"/api/submissions/{sub['id']}/check-summary", headers=auth_headers)
    claim_resp = client.post(
        f"/api/submissions/{sub['id']}/check", json={"claim": "x"}, headers=auth_headers
    )

    assert summary_resp.status_code == 503
    assert "GEMINI_API_KEY" in summary_resp.json()["detail"]
    assert claim_resp.status_code == 503
    # Non-LLM features keep working.
    assert client.get(f"/api/submissions/{sub['id']}", headers=auth_headers).status_code == 200
