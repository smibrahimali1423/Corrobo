export type Verdict = "SUPPORTED" | "CONTRADICTED" | "UNVERIFIABLE" | "ERROR";

export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface SubmissionListItem {
  id: number;
  title: string;
  summary: string;
  chunk_count: number;
  created_at: string;
  check_count: number;
}

export interface CheckResult {
  claim: string;
  verdict: Verdict;
  reason: string;
  evidence: string[];
}

export interface CheckRun {
  id: number;
  submission_id: number;
  model: string;
  created_at: string;
  results: CheckResult[];
  verdict_counts: Record<Verdict, number>;
}

export interface SubmissionDetail {
  id: number;
  title: string;
  source_document: string;
  summary: string;
  chunk_count: number;
  created_at: string;
  check_runs: CheckRun[];
}

export interface Health {
  status: "ok" | "degraded";
  database: boolean;
  llm_configured: boolean;
  model: string;
}
