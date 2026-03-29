import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./features/auth/AuthProvider";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";

function AuthGate() {
  const { isBootstrapping } = useAuth();

  if (isBootstrapping) {
    return (
      <div className="screen-shell">
        <div className="loading-card">Checking your flight deck access...</div>
      </div>
    );
  }

  return <Outlet />;
}

function RequireAuth() {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

function PublicOnly() {
  const { user } = useAuth();

  if (user) {
    return <Navigate to="/app" replace />;
  }

  return <Outlet />;
}

export function App() {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
            staleTime: 60_000,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AuthProvider>
          <Routes>
            <Route element={<AuthGate />}>
              <Route element={<PublicOnly />}>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/signup" element={<SignupPage />} />
              </Route>
              <Route element={<RequireAuth />}>
                <Route path="/app" element={<DashboardPage />} />
              </Route>
              <Route path="/" element={<Navigate to="/app" replace />} />
            </Route>
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
