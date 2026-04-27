import type { ReactNode } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DashboardLovable } from "../pages/dashboard/DashboardLovable";

vi.mock("../components/common/AiInsightCard", () => ({
  AiInsightCard: () => <div>AI Insight Card</div>,
}));

vi.mock("../components/dashboard/RoiSummaryCard", () => ({
  RoiSummaryCard: () => <div>ROI Summary Card</div>,
}));

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children?: ReactNode }) => <div data-testid="responsive-container">{children}</div>,
  AreaChart: ({ data }: { children?: ReactNode; data: unknown[] }) => <div data-testid="area-chart" data-points={data.length} />,
  Area: () => <div data-testid="area-series" />,
  CartesianGrid: () => null,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
}));

const dashboardHooks = vi.hoisted(() => ({
  useExecutiveDashboard: vi.fn(),
  useCommercialDashboard: vi.fn(),
  useOperationalDashboard: vi.fn(),
  useRetentionDashboard: vi.fn(),
  useChurnDashboard: vi.fn(),
  useWeeklySummary: vi.fn(),
  useBIFoundationDashboard: vi.fn(),
}));

vi.mock("../hooks/useDashboard", () => dashboardHooks);

function queryResult<T>(data: T, isLoading = false) {
  return {
    data,
    isLoading,
    isError: false,
    error: null,
    isFetching: false,
  };
}

const executiveData = {
  total_members: 128,
  active_members: 103,
  mrr: 48250,
  churn_rate: 3.8,
  nps_avg: 72,
  risk_distribution: {
    green: 77,
    yellow: 33,
    red: 18,
  },
};

const commercialData = {
  pipeline: {
    new: 12,
    qualified: 9,
    won: 5,
  },
  conversion_by_source: [],
  cac: 210,
  stale_leads_total: 2,
  stale_leads: [
    {
      id: "lead-1",
      full_name: "Lead Maria",
      stage: "qualified",
      source: "instagram",
      last_contact_at: "2026-03-15T10:00:00Z",
    },
  ],
};

const operationalData = {
  realtime_checkins: 84,
  heatmap: [],
  inactive_7d_total: 3,
  inactive_7d_items: [
    {
      id: "member-1",
      full_name: "Ana Silva",
      plan_name: "Plano Mensal",
      loyalty_months: 4,
      last_checkin_at: "2026-03-11T08:00:00Z",
    },
  ],
};

const retentionData = {
  red: {
    total: 2,
    items: [
      {
        id: "member-1",
        full_name: "Ana Silva",
        plan_name: "Plano Mensal",
        risk_score: 88,
        last_checkin_at: "2026-03-10T10:00:00Z",
      },
    ],
  },
  yellow: { total: 4, items: [] },
  nps_trend: [
    { month: "2025-09", average_score: 68, responses: 10 },
    { month: "2025-10", average_score: 69, responses: 12 },
    { month: "2025-11", average_score: 70, responses: 13 },
    { month: "2025-12", average_score: 71, responses: 14 },
    { month: "2026-01", average_score: 72, responses: 15 },
    { month: "2026-02", average_score: 73, responses: 16 },
    { month: "2026-03", average_score: 74, responses: 17 },
  ],
  mrr_at_risk: 6200,
  avg_red_score: 84,
  avg_yellow_score: 57,
  last_contact_map: {},
};

const churnData = [
  { month: "2025-09", churn_rate: 4.8 },
  { month: "2025-10", churn_rate: 4.2 },
  { month: "2025-11", churn_rate: 4.1 },
  { month: "2025-12", churn_rate: 3.9 },
  { month: "2026-01", churn_rate: 3.7 },
  { month: "2026-02", churn_rate: 3.5 },
  { month: "2026-03", churn_rate: 3.8 },
];

const biFoundationData = {
  generated_at: "2026-03-20T10:00:00Z",
  cohort: [{ month: "2026-03", joined: 10, active: 8, retained_rate: 80, mrr: 12000 }],
  ltv: [{ month: "2026-03", ltv: 900 }],
  forecast: [{ horizon_months: 3, projected_revenue: 55000 }],
  revenue_at_risk: 6200,
  revenue_at_risk_members: 6,
  follow_up_impact: {
    prepared_actions_30d: 12,
    positive_outcomes_30d: 7,
    completed_followups_30d: 9,
    retention_contacts_30d: 11,
    acceptance_rate: 58.3,
    data_quality: "ready",
  },
  data_quality_flags: [],
};

const weeklySummaryData = {
  checkins_this_week: 342,
  checkins_last_week: 320,
  checkins_delta_pct: 6.9,
  new_registrations: 12,
  new_at_risk: 3,
  mrr_at_risk: 6200,
  total_active: 103,
};

function renderPage() {
  return render(
    <MemoryRouter>
      <DashboardLovable />
    </MemoryRouter>,
  );
}

describe("DashboardLovable", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    dashboardHooks.useExecutiveDashboard.mockReturnValue(queryResult(executiveData));
    dashboardHooks.useCommercialDashboard.mockReturnValue(queryResult(commercialData));
    dashboardHooks.useOperationalDashboard.mockReturnValue(queryResult(operationalData));
    dashboardHooks.useRetentionDashboard.mockReturnValue(queryResult(retentionData));
    dashboardHooks.useChurnDashboard.mockReturnValue(queryResult(churnData));
    dashboardHooks.useWeeklySummary.mockReturnValue(queryResult(weeklySummaryData));
    dashboardHooks.useBIFoundationDashboard.mockReturnValue(queryResult(biFoundationData));
  });

  it("renders the reorganized dashboard with header, KPIs, weekly summary, chart toggle, AI and ROI", async () => {
    renderPage();

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Visao geral operacional e estrategica da academia")).toBeInTheDocument();

    expect(screen.getByText("Total membros")).toBeInTheDocument();
    expect(screen.getByText("Ativos")).toBeInTheDocument();
    expect(screen.getByText("Churn")).toBeInTheDocument();
    expect(screen.getByText("Receita")).toBeInTheDocument();

    expect(screen.getByText("Resumo semanal")).toBeInTheDocument();
    expect(screen.getByText("Check-ins 7d")).toBeInTheDocument();
    expect(screen.getByText("Novos alunos")).toBeInTheDocument();

    expect(screen.getByTestId("area-chart")).toHaveAttribute("data-points", "6");

    fireEvent.click(screen.getByRole("button", { name: "3M" }));
    await waitFor(() => {
      expect(screen.getByTestId("area-chart")).toHaveAttribute("data-points", "3");
    });

    fireEvent.click(screen.getByRole("button", { name: "Tudo" }));
    await waitFor(() => {
      expect(screen.getByTestId("area-chart")).toHaveAttribute("data-points", "7");
    });

    expect(screen.getByText("AI Insight Card")).toBeInTheDocument();
    expect(screen.getByText("ROI Summary Card")).toBeInTheDocument();
    expect(screen.getByText(/Acoes prioritarias/i)).toBeInTheDocument();
    expect(screen.getAllByText("Ana Silva").length).toBeGreaterThan(0);
    expect(screen.getByText("Lead Maria")).toBeInTheDocument();
  });

  it("shows the empty state when there are no priority actions", async () => {
    dashboardHooks.useCommercialDashboard.mockReturnValue(
      queryResult({ ...commercialData, stale_leads_total: 0, stale_leads: [] }),
    );
    dashboardHooks.useOperationalDashboard.mockReturnValue(
      queryResult({ ...operationalData, inactive_7d_total: 0, inactive_7d_items: [] }),
    );
    dashboardHooks.useRetentionDashboard.mockReturnValue(
      queryResult({ ...retentionData, red: { total: 0, items: [] } }),
    );

    renderPage();

    expect(await screen.findByText("Nenhuma acao prioritaria no momento")).toBeInTheDocument();
    expect(
      screen.getByText("A fila esta sob controle. Volte mais tarde para acompanhar novas oportunidades."),
    ).toBeInTheDocument();
  });

  it("shows a contextual empty state when churn and NPS have no useful historical variation", async () => {
    dashboardHooks.useRetentionDashboard.mockReturnValue(
      queryResult({
        ...retentionData,
        nps_trend: [],
      }),
    );
    dashboardHooks.useChurnDashboard.mockReturnValue(
      queryResult([
        { month: "2025-12", churn_rate: 0 },
        { month: "2026-01", churn_rate: 0 },
        { month: "2026-02", churn_rate: 0 },
        { month: "2026-03", churn_rate: 0 },
      ]),
    );

    renderPage();

    expect(await screen.findByText("Sem base historica util para o grafico")).toBeInTheDocument();
    expect(
      screen.getByText(
        "O piloto ainda nao acumulou NPS ou churn com variacao suficiente. Assim que houver respostas e cancelamentos registrados, a curva aparece aqui com contexto real.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("area-chart")).not.toBeInTheDocument();
  });

  it("does not present financial or churn KPIs as real when the dashboard has no base", () => {
    dashboardHooks.useExecutiveDashboard.mockReturnValue(
      queryResult({
        ...executiveData,
        total_members: 0,
        active_members: 0,
        mrr: 0,
        churn_rate: 0,
      }),
    );
    dashboardHooks.useRetentionDashboard.mockReturnValue(
      queryResult({
        ...retentionData,
        red: { total: 0, items: [] },
        nps_trend: [],
      }),
    );
    dashboardHooks.useChurnDashboard.mockReturnValue(queryResult([]));

    renderPage();

    expect(screen.getAllByText("Sem base").length).toBeGreaterThanOrEqual(2);
  });
});
