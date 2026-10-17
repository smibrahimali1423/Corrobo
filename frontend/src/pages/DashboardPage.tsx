import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import type { SubmissionListItem } from "../types";

export function DashboardPage() {
  const [items, setItems] = useState<SubmissionListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listSubmissions()
      .then(setItems)
      .catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!items) return <p className="muted">Loading…</p>;

  return (
    <>
      <div className="page-head">
        <h1>Your submissions</h1>
        <Link to="/submissions/new" className="button">
          New check
        </Link>
      </div>
      {items.length === 0 ? (
        <div className="card empty">
          <p>No submissions yet.</p>
          <p className="muted">
            Paste a source document and an AI-generated summary of it, and Corrobo will check
            each claim in the summary against the source.
          </p>
        </div>
      ) : (
        <ul className="submission-list">
          {items.map((s) => (
            <li key={s.id} className="card submission-item">
              <Link to={`/submissions/${s.id}`} className="submission-title">
                {s.title}
              </Link>
              <p className="muted clamp">{s.summary}</p>
              <p className="small muted">
                {new Date(s.created_at).toLocaleString()} · {s.chunk_count} chunks ·{" "}
                {s.check_count} {s.check_count === 1 ? "check" : "checks"}
              </p>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
