import { render, screen } from "@testing-library/react";
import { MemoryRouter, Outlet } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import App from "../App";

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    user: { id: "owner-1", full_name: "Owner", role: "owner" },
    loading: false,
    isAuthenticated: true,
  }),
}));

vi.mock("../components/layout/LovableLayout", () => ({
  LovableLayout: () => <Outlet />,
}));

vi.mock("../pages/assessments/BodyCompositionReportPage", () => ({
  default: () => <div>Relatorio antropometrico carregado</div>,
}));

describe("assessment report routes", () => {
  it("loads the lazy anthropometry report inside the guarded suspense boundary", async () => {
    render(
      <MemoryRouter
        initialEntries={[
          "/assessments/members/member-1/anthropometry/assessment-1/report",
        ]}
      >
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Relatorio antropometrico carregado")).toBeInTheDocument();
  });
});
