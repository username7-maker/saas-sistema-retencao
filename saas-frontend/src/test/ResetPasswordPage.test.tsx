import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ResetPasswordPage } from "../pages/auth/ResetPasswordPage";

vi.mock("../services/api", () => ({
  api: {
    post: vi.fn(),
  },
}));

describe("ResetPasswordPage", () => {
  it("prefills the token from the URL hash", () => {
    render(
      <MemoryRouter initialEntries={["/reset-password#token=secure-token-12345"]}>
        <ResetPasswordPage />
      </MemoryRouter>,
    );

    expect(screen.getByDisplayValue("secure-token-12345")).toBeInTheDocument();
  });
});
