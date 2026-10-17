import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api } from "../api";
import { CheckRunView } from "../components/CheckRunView";
import { useHealth } from "../hooks";
import type { SubmissionDetail } from "../types";

export function SubmissionPage() {
  const { id } = useParams();
  const submissionId = Number(id);
  const navigate = useNavigate();
  const health = useHealth();
  const [submission, setSubmission] = useState<SubmissionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    api
      .getSubmission(submissionId)
      .then(setSubmission)
      .catch((e: Error) => setError(e.message));
  }, [submissionId]);

  async function runCheck() {
    if (!submission) return;
    setChecking(true);
    setError(null);
    try {
      const run = await api.checkSummary(submission.id);
      setSubmission({ ...submission, check_runs: [run, ...submission.check_runs] });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Check failed");
    } finally {
      setChecking(false);
    }
  }

  async function remove() {
    if (!submission || !window.confirm("Delete this submission and all its checks?")) return;
    try {
      await api.deleteSubmission(submission.id);
      navigate("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  if (!submission) {
    return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>;
  }

  const llmDisabled = health !== null && !health.llm_configured;
  const [latest, ...older] = submission.check_runs;

  return (
    <>
      <div className="page-head">
        <h1>{submission.title}</h1>
        <div className="actions">
          <button
            type="button"
            className="button"
            onClick={runCheck}
            disabled={checking || llmDisabled}
            title={llmDisabled ? "GEMINI_API_KEY is not configured on the server" : undefined}
          >
            {checking ? "Checking claims…" : "Run check"}
          </button>
          <button type="button" className="button button-ghost" onClick={remove}>
            Delete
          </button>
        </div>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      <div className="two-col">
        <section className="card">
          <h2>Summary</h2>
          <p className="prewrap">{submission.summary}</p>
          <h2>Source document</h2>
          <p className="muted small">{submission.chunk_count} {submission.chunk_count === 1 ? "chunk" : "chunks"} indexed</p>
          <div className="source prewrap">{submission.source_document}</div>
        </section>

        <section>
          <h2>Results</h2>
          {latest ? (
            <CheckRunView run={latest} />
          ) : (
            <div className="card empty">
              <p className="muted">
                No checks yet. Run a check to extract claims from the summary and judge each one
                against the source.
              </p>
            </div>
          )}
          {older.length > 0 && (
            <details className="history">
              <summary>Previous checks ({older.length})</summary>
              {older.map((run) => (
                <CheckRunView key={run.id} run={run} />
              ))}
            </details>
          )}
        </section>
      </div>
    </>
  );
}
