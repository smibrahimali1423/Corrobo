import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth";
import { useHealth } from "../hooks";

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const health = useHealth();

  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">
          <img src="/favicon.svg" alt="" width={22} height={22} /> Corrobo
        </Link>
        {user && (
          <nav className="topnav">
            <Link to="/submissions/new" className="button button-small">
              New check
            </Link>
            <span className="muted small">{user.email}</span>
            <button type="button" className="link-button" onClick={logout}>
              Sign out
            </button>
          </nav>
        )}
      </header>
      {health && !health.llm_configured && (
        <div className="banner" role="status">
          LLM checks are disabled on this server (no <code>GEMINI_API_KEY</code>). You can still
          create submissions and browse past results.
        </div>
      )}
      <main className="content">{children}</main>
    </div>
  );
}
