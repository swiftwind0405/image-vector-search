import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("../pages/DashboardPage", () => ({
  default: () => <h1>Dashboard</h1>,
}));

vi.mock("../components/Layout", () => ({
  default: () => <div>Protected Layout</div>,
}));

import App from "../App";

describe("auth flow", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("keeps the user signed in after logging in from a redirected page", async () => {
    fetchMock.mockImplementation(async (input, init) => {
      const path = String(input);
      if (path === "/api/auth/me") {
        if (fetchMock.mock.calls.filter(([url]) => String(url) === "/api/auth/me").length === 1) {
          return new Response(JSON.stringify({ authenticated: false }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        await new Promise((resolve) => setTimeout(resolve, 50));
        return new Response(JSON.stringify({ authenticated: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (path === "/api/auth/login" && init?.method === "POST") {
        return new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      throw new Error(`Unhandled request: ${init?.method ?? "GET"} ${path}`);
    });

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, refetchOnWindowFocus: false },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/"]}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const user = userEvent.setup();

    expect(await screen.findByRole("heading", { name: "Image Search Archive", level: 2 })).toBeInTheDocument();
    expect(screen.getAllByText("Curate, search, and organize your indexed image library.")[0]).toBeInTheDocument();

    await user.type(screen.getByLabelText("Username"), "admin");
    await user.type(screen.getByLabelText("Password"), "secret");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(screen.getByText("Protected Layout")).toBeInTheDocument();
    });
    expect(screen.queryByRole("heading", { name: "Image Search Archive", level: 2 })).not.toBeInTheDocument();
  });
});
