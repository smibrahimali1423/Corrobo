import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";

export function NewSubmissionPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [source, setSource] = useState("");
  const [summary, setSummary] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const created = await api.createSubmission({
        title: title.trim() || undefined,
        source_document: source,
        summary,
      });
      navigate(`/submissions/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create submission");
      setBusy(false);
    }
  }

  return (
    <>
      <h1>New check</h1>
      <form onSubmit={onSubmit} className="form card">
        <label>
          Title <span className="muted small">(optional)</span>
          <input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} />
        </label>
        <label>
          Source document
          <textarea
            value={source}
            onChange={(e) => setSource(e.target.value)}
            rows={12}
            placeholder="Paste the original text (e.g. a clinical note or paper abstract)…"
            required
          />
        </label>
        <label>
          AI-generated summary
          <textarea
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            rows={6}
            placeholder="Paste the summary you want to fact-check…"
            required
          />
        </label>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="button" disabled={busy}>
          {busy ? "Indexing source…" : "Save and index"}
        </button>
      </form>
    </>
  );
}
