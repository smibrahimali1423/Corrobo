from judge import Judgment


def _mock_chunking_and_storage(monkeypatch):
    monkeypatch.setattr("main.chunk_text", lambda text, **kwargs: ["chunk one", "chunk two"])
    monkeypatch.setattr("main.store_chunks", lambda submission_id, chunks: None)


def test_create_submission_chunks_and_stores(client, monkeypatch):
    stored = {}

    def fake_store_chunks(submission_id, chunks):
        stored["submission_id"] = submission_id
        stored["chunks"] = chunks

    monkeypatch.setattr("main.chunk_text", lambda text, **kwargs: ["chunk one", "chunk two"])
    monkeypatch.setattr("main.store_chunks", fake_store_chunks)

    response = client.post(
        "/submissions",
        json={"source_document": "Some source text.", "summary": "A summary."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_document"] == "Some source text."
    assert stored["submission_id"] == body["id"]
    assert stored["chunks"] == ["chunk one", "chunk two"]


def test_list_submissions_returns_created_rows(client, monkeypatch):
    _mock_chunking_and_storage(monkeypatch)

    client.post("/submissions", json={"source_document": "doc", "summary": "sum"})
    response = client.get("/submissions")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_check_claim_returns_judgment(client, monkeypatch):
    _mock_chunking_and_storage(monkeypatch)
    monkeypatch.setattr("main.retrieve_relevant_chunks", lambda sid, claim, k=5: ["some evidence"])
    monkeypatch.setattr(
        "main.judge_claim",
        lambda claim, evidence: Judgment(verdict="SUPPORTED", reason="looks right"),
    )

    create_resp = client.post("/submissions", json={"source_document": "doc", "summary": "sum"})
    submission_id = create_resp.json()["id"]

    response = client.post(f"/submissions/{submission_id}/check", json={"claim": "A claim."})

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "SUPPORTED"
    assert body["evidence"] == ["some evidence"]


def test_check_summary_returns_one_result_per_claim(client, monkeypatch):
    _mock_chunking_and_storage(monkeypatch)
    monkeypatch.setattr("main.retrieve_relevant_chunks", lambda sid, claim, k=5: ["evidence"])
    monkeypatch.setattr("main.extract_claims", lambda summary: ["Claim A.", "Claim B."])
    monkeypatch.setattr(
        "main.judge_claim",
        lambda claim, evidence: Judgment(verdict="SUPPORTED", reason="ok"),
    )

    create_resp = client.post("/submissions", json={"source_document": "doc", "summary": "sum"})
    submission_id = create_resp.json()["id"]

    response = client.post(f"/submissions/{submission_id}/check-summary")

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    assert {r["claim"] for r in results} == {"Claim A.", "Claim B."}


def test_check_summary_missing_submission_returns_404(client):
    response = client.post("/submissions/999999/check-summary")
    assert response.status_code == 404


def test_check_summary_partial_failure_does_not_lose_other_results(client, monkeypatch):
    _mock_chunking_and_storage(monkeypatch)
    monkeypatch.setattr("main.retrieve_relevant_chunks", lambda sid, claim, k=5: ["evidence"])
    monkeypatch.setattr(
        "main.extract_claims", lambda summary: ["Claim A.", "Claim B.", "Claim C."]
    )

    def flaky_judge_claim(claim, evidence):
        if claim == "Claim B.":
            raise RuntimeError("simulated transient failure")
        return Judgment(verdict="SUPPORTED", reason="ok")

    monkeypatch.setattr("main.judge_claim", flaky_judge_claim)

    create_resp = client.post("/submissions", json={"source_document": "doc", "summary": "sum"})
    submission_id = create_resp.json()["id"]

    response = client.post(f"/submissions/{submission_id}/check-summary")

    assert response.status_code == 200
    by_claim = {r["claim"]: r for r in response.json()}
    assert by_claim["Claim A."]["verdict"] == "SUPPORTED"
    assert by_claim["Claim B."]["verdict"] == "ERROR"
    assert by_claim["Claim C."]["verdict"] == "SUPPORTED"
