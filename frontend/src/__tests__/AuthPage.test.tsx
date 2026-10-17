import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { getToken } from "../api";
import { AuthProvider } from "../auth";
import { AuthPage } from "../pages/AuthPage";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

function renderLogin() {
  render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <AuthPage mode="login" />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("AuthPage", () => {
  it("stores the token after a successful login", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 200,
        ok: true,
        json: () =>
          Promise.resolve({
            access_token: "tok-123",
            token_type: "bearer",
            user: { id: 1, email: "a@b.co", created_at: "2026-01-01T00:00:00Z" },
          }),
      }),
    );
    renderLogin();

    await userEvent.type(screen.getByLabelText("Email"), "a@b.co");
    await userEvent.type(screen.getByLabelText("Password"), "secret-pass");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(getToken()).toBe("tok-123");
  });

  it("shows the server error on bad credentials", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 401,
        ok: false,
        json: () => Promise.resolve({ detail: "Invalid email or password" }),
      }),
    );
    renderLogin();

    await userEvent.type(screen.getByLabelText("Email"), "a@b.co");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password");
    expect(getToken()).toBeNull();
  });
});
