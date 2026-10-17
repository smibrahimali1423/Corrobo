import { useState } from "react";

import type { CheckResult, CheckRun } from "../types";
import { VerdictBadge, VerdictSummary } from "./VerdictBadge";

function ClaimRow({ result }: { result: CheckResult }) {
  const [open, setOpen] = useState(false);
  return (
    <li className={`claim claim-${result.verdict.toLowerCase()}`}>
      <div className="claim-head">
        <VerdictBadge verdict={result.verdict} />
        <span className="claim-text">{result.claim}</span>
      </div>
      <p className="claim-reason">{result.reason}</p>
      {result.evidence.length > 0 && (
        <>
          <button type="button" className="link-button" onClick={() => setOpen((o) => !o)}>
            {open ? "Hide" : "Show"} evidence ({result.evidence.length})
          </button>
          {open && (
            <ol className="evidence">
              {result.evidence.map((chunk, i) => (
                <li key={i}>{chunk}</li>
              ))}
            </ol>
          )}
        </>
      )}
    </li>
  );
}

export function CheckRunView({ run }: { run: CheckRun }) {
  return (
    <section className="check-run">
      <header className="check-run-head">
        <VerdictSummary counts={run.verdict_counts} />
        <span className="muted small">
          {new Date(run.created_at).toLocaleString()} · {run.model}
        </span>
      </header>
      <ul className="claims">
        {run.results.map((r, i) => (
          <ClaimRow key={i} result={r} />
        ))}
      </ul>
    </section>
  );
}
