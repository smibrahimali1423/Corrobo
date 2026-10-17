import type {
  CheckResult,
  CheckRun,
  Health,
  SubmissionDetail,
  SubmissionListItem,
  TokenResponse,
  User,
} from "./types";

const TOKEN_KEY = "corrobo.token";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

/** FastAPI errors are `{detail: string}` or, for validation, `{detail: [{msg}]}`. */
function errorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : String(d)))
        .join("; ");
    }
  }
  return fallback;
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const resp = await fetch(`/api${path}`, { ...options, headers });
  if (resp.status === 204) return undefined as T;

  const body: unknown = await resp.json().catch(() => null);
  if (!resp.ok) {
    if (resp.status === 401) setToken(null);
    throw new ApiError(resp.status, errorMessage(body, `Request failed (${resp.status})`));
  }
  return body as T;
}

const post = <T>(path: string, data?: unknown) =>
  request<T>(path, { method: "POST", body: data === undefined ? undefined : JSON.stringify(data) });

export const api = {
  health: () => request<Health>("/health"),
  register: (email: string, password: string) =>
    post<TokenResponse>("/auth/register", { email, password }),
  login: (email: string, password: string) =>
    post<TokenResponse>("/auth/login", { email, password }),
  me: () => request<User>("/auth/me"),
  listSubmissions: () => request<SubmissionListItem[]>("/submissions"),
  getSubmission: (id: number) => request<SubmissionDetail>(`/submissions/${id}`),
  createSubmission: (data: { title?: string; source_document: string; summary: string }) =>
    post<SubmissionDetail>("/submissions", data),
  deleteSubmission: (id: number) => request<void>(`/submissions/${id}`, { method: "DELETE" }),
  checkSummary: (id: number) => post<CheckRun>(`/submissions/${id}/check-summary`),
  checkClaim: (id: number, claim: string) =>
    post<CheckResult>(`/submissions/${id}/check`, { claim }),
};
