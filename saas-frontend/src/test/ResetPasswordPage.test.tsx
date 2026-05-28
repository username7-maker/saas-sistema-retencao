import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ResetPasswordPage } from "../pages/auth/ResetPasswordPage";
import { api } from "../services/api";

const toastMocks = vi.hoisted(() => ({
  error: vi.fn(),
  success: vi.fn(),
}));

vi.mock("../services/api", () => ({
  api: {
    post: vi.fn(),
  },
}));

vi.mock("react-hot-toast", () => ({
  default: {
    error: toastMocks.error,
    success: toastMocks.success,
  },
}));

describe("ResetPasswordPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("prefills the token from the URL hash", () => {
    render(
      <MemoryRouter initialEntries={["/reset-password#token=secure-token-12345"]}>
        <ResetPasswordPage />
      </MemoryRouter>,
    );

    expect(screen.getByDisplayValue("secure-token-12345")).toBeInTheDocument();
  });

  it("posts the token and new password to the reset endpoint", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { message: "ok" } });
    render(
      <MemoryRouter initialEntries={["/reset-password#token=secure-token-12345"]}>
        <ResetPasswordPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByPlaceholderText("Minimo de 8 caracteres"), { target: { value: "NewPass123" } });
    fireEvent.change(screen.getByPlaceholderText("Repita a nova senha"), { target: { value: "NewPass123" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar nova senha" }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/api/v1/auth/reset-password", {
        token: "secure-token-12345",
        new_password: "NewPass123",
      });
    });
    expect(toastMocks.success).toHaveBeenCalledWith("Senha redefinida com sucesso. Entre com a nova senha.");
  });
});
