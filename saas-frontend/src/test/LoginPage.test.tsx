import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginPage } from "../pages/auth/LoginPage";
import { api } from "../services/api";

const mocks = vi.hoisted(() => ({
  login: vi.fn(),
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    login: mocks.login,
  }),
}));

vi.mock("../services/api", () => ({
  api: {
    post: vi.fn(),
  },
}));

vi.mock("react-hot-toast", () => ({
  default: {
    error: mocks.toastError,
    success: mocks.toastSuccess,
  },
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("exposes password recovery from the login form", () => {
    renderPage();

    expect(screen.getByRole("button", { name: "Esqueci minha senha" })).toBeInTheDocument();
  });

  it("submits gym slug and email to the forgot password endpoint", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { message: "ok" } });
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Esqueci minha senha" }));
    fireEvent.change(screen.getByPlaceholderText("academia-centro"), { target: { value: "cordex-gym" } });
    fireEvent.change(screen.getByPlaceholderText("gestor@academia.com"), { target: { value: "owner@cordex.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar link de redefinicao" }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/api/v1/auth/forgot-password", {
        gym_slug: "cordex-gym",
        email: "owner@cordex.com",
      });
    });
    expect(mocks.toastSuccess).toHaveBeenCalledWith("Se o e-mail estiver cadastrado, enviaremos as instrucoes.");
  });
});
