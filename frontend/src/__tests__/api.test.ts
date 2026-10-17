import { afterEach, describe, expect, it, vi } from "vitest";

import { api, ApiError, getToken, setToken } from "../api";

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn().mockResolvedValue({
    status,
    ok: status >= 200 && status < 300,
    json: () => Promise.resolve(body),
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("api client", () => {
  it("sends the bearer token and JSON body", async () => {
    setToken("abc");
    const fetchFn = mockFetch(201, { id: 1 });

    await api.createSubmission({ source_document: "doc", summary: "sum" });

    const [url, init] = fetchFn.mock.calls[0];
    expect(url).toBe("/api/submissions");
    expect(init.method).toBe("POST");
    expect(init.headers.get("Authorization")).toBe("Bearer abc");
    expect(init.headers.get("Content-Type")).toBe("application/json");
    expect(JSON.parse(init.body)).toEqual({ source_document: "doc", summary: "sum" });
  });

  it("surfaces FastAPI string error details", async () => {
    mockFetch(503, { detail: "LLM checks are unavailable" });
    await expect(api.checkSummary(1)).rejects.toThrow("LLM checks are unavailable");
  });

  it("joins validation error messages", async () => {
    mockFetch(422, { detail: [{ msg: "too short" }, { msg: "bad email" }] });
    await expect(api.register("x", "y")).rejects.toThrow("too short; bad email");
  });

  it("clears the stored token on 401", async () => {
    setToken("expired");
    mockFetch(401, { detail: "Not authenticated" });

    const err = await api.me().catch((e) => e);

    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(401);
    expect(getToken()).toBeNull();
  });
});
