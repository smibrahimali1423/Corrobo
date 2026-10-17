import type { Verdict } from "../types";

const LABELS: Record<Verdict, string> = {
  SUPPORTED: "Supported",
  CONTRADICTED: "Contradicted",
  UNVERIFIABLE: "Unverifiable",
  ERROR: "Error",
};

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return <span className={`badge badge-${verdict.toLowerCase()}`}>{LABELS[verdict]}</span>;
}

export function VerdictSummary({ counts }: { counts: Record<Verdict, number> }) {
  const order: Verdict[] = ["SUPPORTED", "CONTRADICTED", "UNVERIFIABLE", "ERROR"];
  const total = order.reduce((sum, v) => sum + (counts[v] ?? 0), 0);
  if (total === 0) return <p className="muted">No claims were extracted from this summary.</p>;

  return (
    <div className="verdict-summary" aria-label="Verdict summary">
      {order
        .filter((v) => counts[v] > 0)
        .map((v) => (
          <span key={v} className={`summary-pill badge-${v.toLowerCase()}`}>
            <strong>{counts[v]}</strong> {LABELS[v].toLowerCase()}
          </span>
        ))}
      <span className="muted">of {total} claims</span>
    </div>
  );
}
