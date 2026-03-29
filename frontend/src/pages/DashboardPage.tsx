import { useNavigate } from "react-router-dom";

import { useAuth } from "../features/auth/AuthProvider";

export function DashboardPage() {
  const navigate = useNavigate();
  const { logout, user, isSubmitting } = useAuth();

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <div className="screen-shell">
      <section className="dashboard-shell">
        <header className="dashboard-header">
          <div>
            <p className="eyebrow">Authenticated</p>
            <h1>Airzone flight deck</h1>
            <p className="summary">
              Signed in as <strong>{user?.email}</strong>. The map search interface lands in the
              next stage; this shell already protects the app and keeps the session warm.
            </p>
          </div>
          <button className="ghost-button" onClick={handleLogout} disabled={isSubmitting}>
            Sign out
          </button>
        </header>
        <div className="dashboard-panels">
          <article className="feature-card">
            <h2>Secure entry</h2>
            <p>
              Cookie-based sessions flow through the FastAPI backend, and the React app boots from
              `/auth/me` so refreshes stay seamless.
            </p>
          </article>
          <article className="feature-card">
            <h2>Backend ready</h2>
            <p>
              Live OpenSky search, geocoding, and aviationstack enrichment are already available for
              the map UI to consume next.
            </p>
          </article>
        </div>
      </section>
    </div>
  );
}

