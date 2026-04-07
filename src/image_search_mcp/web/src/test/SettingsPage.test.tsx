import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockUseEmbeddingSettings = vi.fn();
const mockMutateAsync = vi.fn();

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("@/api/settings", () => ({
  useEmbeddingSettings: () => mockUseEmbeddingSettings(),
  useUpdateEmbeddingSettings: () => ({
    isPending: false,
    mutateAsync: mockMutateAsync,
  }),
}));

import { toast } from "sonner";
import SettingsPage from "../pages/SettingsPage";

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("SettingsPage", () => {
  beforeEach(() => {
    mockMutateAsync.mockReset();
    mockUseEmbeddingSettings.mockReset();
    mockUseEmbeddingSettings.mockReturnValue({
      data: {
        provider: "jina",
        jina_api_key_configured: true,
        google_api_key_configured: false,
        using_environment_fallback: false,
      },
      isLoading: false,
    });
  });

  it("renders masked configured state", () => {
    renderPage();

    expect(screen.getByText("Embedding Configuration")).toBeInTheDocument();
    expect(screen.getByDisplayValue("jina")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("••••••")).toBeInTheDocument();
    expect(screen.getByText("Configured")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save Settings" })).toBeDisabled();
  });

  it("keeps save disabled when there are no changes", () => {
    renderPage();

    expect(screen.getByRole("button", { name: "Save Settings" })).toBeDisabled();
  });

  it("submits null for untouched key fields", async () => {
    const user = userEvent.setup();
    mockMutateAsync.mockResolvedValue({
      provider: "gemini",
      jina_api_key_configured: true,
      google_api_key_configured: true,
      using_environment_fallback: false,
    });

    renderPage();

    await user.selectOptions(screen.getByLabelText("Embedding Provider"), "gemini");
    await user.type(screen.getByLabelText("Google API Key"), "google-key");
    await user.click(screen.getByRole("button", { name: "Save Settings" }));

    expect(mockMutateAsync).toHaveBeenCalledWith({
      provider: "gemini",
      jina_api_key: null,
      google_api_key: "google-key",
    });
  });

  it("shows success toast after save", async () => {
    const user = userEvent.setup();
    mockMutateAsync.mockResolvedValue({
      provider: "gemini",
      jina_api_key_configured: false,
      google_api_key_configured: true,
      using_environment_fallback: false,
    });

    renderPage();

    await user.selectOptions(screen.getByLabelText("Embedding Provider"), "gemini");
    await user.type(screen.getByLabelText("Google API Key"), "google-key");
    await user.click(screen.getByRole("button", { name: "Save Settings" }));

    expect(toast.success).toHaveBeenCalledWith("Settings saved");
  });

  it("shows 422 error detail as toast", async () => {
    const user = userEvent.setup();
    mockMutateAsync.mockRejectedValue({
      status: 422,
      message: "{\"detail\":\"No API key configured for provider 'gemini'\"}",
    });

    renderPage();

    await user.selectOptions(screen.getByLabelText("Embedding Provider"), "gemini");
    await user.click(screen.getByRole("button", { name: "Save Settings" }));

    expect(toast.error).toHaveBeenCalledWith("No API key configured for provider 'gemini'");
  });

  it("shows retry button after reload failure", async () => {
    const user = userEvent.setup();
    mockMutateAsync.mockRejectedValue({
      status: 500,
      message: "{\"detail\":\"Settings saved but embedding reload failed: timeout\"}",
    });

    renderPage();

    await user.type(screen.getByLabelText("Jina API Key"), "new-secret");
    await user.click(screen.getByRole("button", { name: "Save Settings" }));

    expect(toast.error).toHaveBeenCalledWith("Settings saved but reload failed - try again");
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("shows unconfigured warning banner", () => {
    mockUseEmbeddingSettings.mockReturnValue({
      data: {
        provider: "",
        jina_api_key_configured: false,
        google_api_key_configured: false,
        using_environment_fallback: false,
      },
      isLoading: false,
    });

    renderPage();

    expect(screen.getByText("Embedding not configured")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save Settings" })).toBeDisabled();
  });

  it("shows environment variable note when using env fallback", () => {
    mockUseEmbeddingSettings.mockReturnValue({
      data: {
        provider: "jina",
        jina_api_key_configured: true,
        google_api_key_configured: false,
        using_environment_fallback: true,
      },
      isLoading: false,
    });

    renderPage();

    expect(screen.getByText("Currently using environment variable")).toBeInTheDocument();
  });

  it("disables save and shows validation when a dirty key is cleared", async () => {
    const user = userEvent.setup();

    renderPage();

    const jinaInput = screen.getByLabelText("Jina API Key");
    await user.type(jinaInput, "abc");
    await user.clear(jinaInput);

    expect(screen.getByText("API key cannot be empty")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save Settings" })).toBeDisabled();
  });
});
