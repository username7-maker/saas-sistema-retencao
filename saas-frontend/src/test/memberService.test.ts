import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../services/api";
import { memberService } from "../services/memberService";

vi.mock("../services/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("memberService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("normalizes legacy array responses and malformed member fields", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: [
        {
          id: 123,
          full_name: null,
          email: 456,
          status: null,
          plan_name: null,
          monthly_fee: null,
          join_date: null,
          preferred_shift: undefined,
          nps_last_score: "bad",
          loyalty_months: "4",
          risk_score: "42.8",
          risk_level: "critical",
          last_checkin_at: undefined,
          extra_data: "bad-extra-data",
          lifecycle_next_focus: { text: "object child would crash React" },
          created_at: null,
          updated_at: null,
        },
      ],
    });

    const result = await memberService.listMembers({ page: 2, page_size: 20 });

    expect(api.get).toHaveBeenCalledWith("/api/v1/members/", {
      params: { page_size: 20, page: 2 },
    });
    expect(result).toEqual({
      items: [
        expect.objectContaining({
          id: "123",
          full_name: "Sem nome",
          email: "456",
          status: "active",
          plan_name: "Plano nao informado",
          monthly_fee: 0,
          join_date: "",
          preferred_shift: null,
          nps_last_score: 0,
          loyalty_months: 4,
          risk_score: 42,
          risk_level: "green",
          last_checkin_at: null,
          extra_data: {},
          lifecycle_next_focus: null,
          created_at: "",
          updated_at: "",
        }),
      ],
      total: 1,
      page: 2,
      page_size: 20,
    });
  });

  it("normalizes paginated responses without losing valid values", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        items: [
          {
            id: "member-1",
            full_name: "Ana Silva",
            email: "ana@example.invalid",
            status: "paused",
            plan_name: "Plano Anual",
            monthly_fee: "199,90",
            join_date: "2026-07-01",
            preferred_shift: "morning",
            nps_last_score: 9,
            loyalty_months: 12,
            risk_score: 10,
            risk_level: "yellow",
            last_checkin_at: "2026-07-10T10:00:00Z",
            extra_data: { external_id: "MAT-001" },
            lifecycle_next_focus: "Fazer contato",
            created_at: "2026-07-01T00:00:00Z",
            updated_at: "2026-07-10T00:00:00Z",
          },
        ],
        total: "34",
        page: "1",
        page_size: "20",
      },
    });

    const result = await memberService.listMembers();

    expect(result.total).toBe(34);
    expect(result.page).toBe(1);
    expect(result.page_size).toBe(20);
    expect(result.items[0]).toEqual(
      expect.objectContaining({
        id: "member-1",
        full_name: "Ana Silva",
        status: "paused",
        monthly_fee: 199.9,
        risk_level: "yellow",
        extra_data: { external_id: "MAT-001" },
        lifecycle_next_focus: "Fazer contato",
      }),
    );
  });

  it("rejects HTML fallback responses instead of showing an empty list", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: "<!doctype html><html><body>SPA fallback</body></html>",
    });

    await expect(memberService.listMembers()).rejects.toThrow("Resposta invalida ao carregar membros.");
  });
});
