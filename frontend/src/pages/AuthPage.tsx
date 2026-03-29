import { FormEvent, ReactNode, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../features/auth/AuthProvider";

type AuthPageProps = {
  mode: "login" | "signup";
  title: string;
  eyebrow: string;
  actionLabel: string;
  alternateLabel: string;
  alternatePath: string;
  alternateAction: string;
  summary: ReactNode;
};

export function AuthPage({
  mode,
  title,
  eyebrow,
  actionLabel,
  alternateLabel,
  alternatePath,
  alternateAction,
  summary,
}: AuthPageProps) {
  const navigate = useNavigate();
  const { login, register, isSubmitting, errorMessage } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (mode === "login") {
      await login({ email, password });
    } else {
      await register({ email, password });
    }

    navigate("/app");
  }

  return (
    <div className="screen-shell">
      <section className="auth-hero">
        <div className="auth-copy">
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p className="summary">{summary}</p>
        </div>
        <div className="auth-card">
          <form className="auth-form" onSubmit={handleSubmit}>
            <label>
              <span>Email</span>
              <input
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="pilot@example.com"
                required
              />
            </label>
            <label>
              <span>Password</span>
              <input
                type="password"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="At least 8 characters"
                minLength={8}
                required
              />
            </label>
            {errorMessage ? <p className="error-banner">{errorMessage}</p> : null}
            <button type="submit" className="primary-button" disabled={isSubmitting}>
              {isSubmitting ? "Contacting tower..." : actionLabel}
            </button>
          </form>
          <p className="auth-switch">
            {alternateLabel} <Link to={alternatePath}>{alternateAction}</Link>
          </p>
        </div>
      </section>
    </div>
  );
}

