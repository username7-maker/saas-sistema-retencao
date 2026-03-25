import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MembersPage } from "../pages/members/MembersPage";
import { memberService } from "../services/memberService";
import type { Member, PaginatedResponse } from "../types";

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    user: { id: "manager-1", full_name: "Manager Teste", role: "manager" },
  }),
}));

vi.mock("../services/memberService", async () => {
  const actual = await vi.importActual<typeof import("../services/memberService")>("../services/memberService");
  return {
    ...actual,
    memberService: {
      ...actual.memberService,
      listMembers: vi.fn(),
      deleteMember: vi.fn(),
    },
  };
});

vi.mock("../pages/members/AddMemberDrawer", () => ({
  AddMemberDrawer: () => null,
}));

vi.mock("../pages/members/EditMemberDrawer", () => ({
  EditMemberDrawer: () => null,
}));

vi.mock("../pages/members/MemberDetailDrawer", () => ({
  MemberDetailDrawer: ({ open }: { open: boolean }) => (open ? <div>drawer aberto</div> : null),
}));

function LocationEcho() {
  const location = useLocation();
  return <div>{location.pathname}</div>;
}

function formatIsoDate(offsetDays: number): string {
  const reference = new Date();
  const next = new Date(reference.getFullYear(), reference.getMonth(), reference.getDate() + offsetDays);
  const year = next.getFullYear();
  const month = String(next.getMonth() + 1).padStart(2, "0");
  const day = String(next.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function makeMember(
  id: string,
  full_name: string,
  extra_data: Record<string, unknown> = {},
  birthdate?: string | null,
): Member {
  return {
    id,
    full_name,
    email: `${id}@teste.com`,
    phone: null,
    birthdate: birthdate ?? null,
    status: "active",
    plan_name: "Plano Mensal",
    monthly_fee: 199.9,
    join_date: "2026-01-10",
    preferred_shift: null,
    nps_last_score: 9,
    loyalty_months: 2,
    risk_score: 34,
    risk_level: "yellow",
    last_checkin_at: "2026-03-17T10:00:00Z",
    extra_data,
    suggested_action: null,
    onboarding_status: "active",
    onboarding_score: 72,
    created_at: "2026-01-10T00:00:00Z",
    updated_at: "2026-03-17T00:00:00Z",
  };
}

const membersResponse: PaginatedResponse<Member> = {
  items: [
    makeMember("member-1", "Ana Silva", { external_id: "MAT-001", provisional_member: true }, formatIsoDate(2)),
    makeMember("member-2", "Bruno Lima"),
  ],
  total: 2,
  page: 1,
  page_size: 20,
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/members"]}>
        <Routes>
          <Route path="/members" element={<MembersPage />} />
          <Route path="/assessments/members/:memberId" element={<LocationEcho />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("MembersPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(memberService.listMembers).mockResolvedValue(membersResponse);
    vi.mocked(memberService.deleteMember).mockResolvedValue();
  });

  it("navigates to the student workspace when clicking the member name", async () => {
    renderPage();

    const memberLink = await screen.findByRole("link", { name: "Ana Silva" });
    fireEvent.click(memberLink);

    expect(screen.getByText("/assessments/members/member-1")).toBeInTheDocument();
    expect(screen.queryByText("drawer aberto")).not.toBeInTheDocument();
  });

  it("keeps the row click opening the quick detail drawer", async () => {
    renderPage();

    const planCells = await screen.findAllByText("Plano Mensal");
    fireEvent.click(planCells[0]);

    expect(screen.getByText("drawer aberto")).toBeInTheDocument();
  });

  it("exposes operational filters and sends them to the member query", async () => {
    renderPage();

    expect(await screen.findByText("Ana Silva")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Buscar por nome, email ou matricula...")).toBeInTheDocument();
    expect(screen.getByText("Matricula MAT-001")).toBeInTheDocument();
    expect(screen.getByText("Provisorio")).toBeInTheDocument();
    expect(screen.getByText("Aniversário em 2 dias")).toBeInTheDocument();

    fireEvent.change(screen.getByRole("combobox", { name: "Sem check-in" }), {
      target: { value: "14" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: "Provisorios" }), {
      target: { value: "exclude" },
    });

    await waitFor(() => {
      expect(memberService.listMembers).toHaveBeenLastCalledWith(
        expect.objectContaining({
          min_days_without_checkin: 14,
          provisional_only: false,
          page: 1,
          page_size: 20,
        }),
      );
    });
  });
});
