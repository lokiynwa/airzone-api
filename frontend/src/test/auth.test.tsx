import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";

const fetchMock = vi.fn();

describe("authentication shell", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    cleanup();
    fetchMock.mockReset();
    window.history.pushState({}, "", "/");
  });

  it("logs a user in and navigates to the app shell", async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Authentication required." }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ user: { id: 1, email: "pilot@example.com" } }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

    window.history.pushState({}, "", "/login");
    const user = userEvent.setup();

    render(<App />);

    await user.type(await screen.findByLabelText(/email/i), "pilot@example.com");
    await user.type(screen.getByLabelText(/password/i), "supersecure");
    await user.click(screen.getByRole("button", { name: /log in/i }));

    await screen.findByText(/airzone flight deck/i);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/login",
      expect.objectContaining({
        credentials: "include",
        method: "POST",
      }),
    );
  });

  it("restores a logged-in session on refresh", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ user: { id: 1, email: "pilot@example.com" } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    window.history.pushState({}, "", "/app");
    render(<App />);

    await waitFor(() =>
      expect(screen.getByText(/the map search interface lands in the next stage/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/signed in as/i)).toHaveTextContent("pilot@example.com");
  });
});
