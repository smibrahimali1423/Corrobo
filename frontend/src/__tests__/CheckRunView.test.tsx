import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { CheckRunView } from "../components/CheckRunView";
import type { CheckRun } from "../types";

const run: CheckRun = {
  id: 1,
  submission_id: 1,
  model: "gemini-test",
  created_at: "2026-10-17T12:00:00Z",
  verdict_counts: { SUPPORTED: 1, CONTRADICTED: 1, UNVERIFIABLE: 0, ERROR: 0 },
  results: [
    { claim: "Drug X reduced mortality.", verdict: "SUPPORTED", reason: "Matches.", evidence: ["Mortality fell from 27% to 18%."] },
    { claim: "Drug X was given IV.", verdict: "CONTRADICTED", reason: "It was oral.", evidence: [] },
  ],
};

describe("CheckRunView", () => {
  it("renders the verdict summary and each claim", () => {
    render(<CheckRunView run={run} />);

    expect(screen.getByLabelText("Verdict summary")).toHaveTextContent("1 supported");
    expect(screen.getByLabelText("Verdict summary")).toHaveTextContent("1 contradicted");
    expect(screen.getByText("Drug X reduced mortality.")).toBeInTheDocument();
    expect(screen.getByText("Contradicted")).toBeInTheDocument();
  });

  it("toggles evidence on demand", async () => {
    render(<CheckRunView run={run} />);

    expect(screen.queryByText("Mortality fell from 27% to 18%.")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Show evidence (1)" }));
    expect(screen.getByText("Mortality fell from 27% to 18%.")).toBeInTheDocument();
  });

  it("explains an empty run", () => {
    render(
      <CheckRunView
        run={{ ...run, results: [], verdict_counts: { SUPPORTED: 0, CONTRADICTED: 0, UNVERIFIABLE: 0, ERROR: 0 } }}
      />,
    );
    expect(screen.getByText(/No claims were extracted/)).toBeInTheDocument();
  });
});
