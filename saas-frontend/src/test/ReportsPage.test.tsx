import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ReportsPage from "../pages/reports/ReportsPage";
import { reportService } from "../services/reportService";

vi.mock("../services/reportService", () => ({
  reportService: {
    exportDashboardPdf: vi.fn(),
    dispatchMonthlyReports: vi.fn(),
    getMonthlyDispatchStatus: vi.fn(),
  },
}));

vi.mock("react-hot-toast", () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ReportsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(reportService.exportDashboardPdf).mockResolvedValue();
    vi.mocked(reportService.dispatchMonthlyReports).mockResolvedValue({
      message: "Disparo mensal enfileirado.",
      job_id: "job-1",
      job_type: "monthly_reports_dispatch",
      status: "pending",
    });
    vi.mocked(reportService.getMonthlyDispatchStatus).mockResolvedValue({
      job_id: "job-1",
      job_type: "monthly_reports_dispatch",
      status: "completed",
      attempt_count: 1,
      max_attempts: 4,
      result: { sent: 2, failed: 0 },
      error_code: null,
      error_message: null,
      next_retry_at: null,
      started_at: null,
      completed_at: null,
      related_entity_type: null,
      related_entity_id: null,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders the premium catalog and downloads a management report", async () => {
    renderPage();

    expect(screen.getByRole("heading", { name: "Relatorios" })).toBeInTheDocument();
    expect(screen.getByText("Board packs de gestao")).toBeInTheDocument();
    expect(screen.getByText("Laudos de avaliacao")).toBeInTheDocument();
    expect(screen.getByText("Resumo do aluno")).toBeInTheDocument();

    const executiveCard = screen.getByText("Executivo").closest("article");
    expect(executiveCard).not.toBeNull();

    fireEvent.click(within(executiveCard as HTMLElement).getByRole("button", { name: "Baixar PDF premium" }));

    await waitFor(() => {
      expect(reportService.exportDashboardPdf).toHaveBeenCalledWith("executive");
    });
  });

  it("tracks monthly dispatch status in the premium distribution card", async () => {
    const setTimeoutSpy = vi.spyOn(window, "setTimeout").mockImplementation(((callback: TimerHandler) => {
      if (typeof callback === "function") {
        queueMicrotask(() => {
          act(() => {
            callback();
          });
        });
      }
      return 0 as unknown as number;
    }) as typeof window.setTimeout);
    const clearTimeoutSpy = vi.spyOn(window, "clearTimeout").mockImplementation(() => {});

    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Disparar relatorio mensal" }));
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Confirmar envio" }));
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(reportService.dispatchMonthlyReports).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(reportService.getMonthlyDispatchStatus).toHaveBeenCalledWith("job-1");
    });

    expect(await screen.findByText("Concluido")).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes("Enviados:"))).toBeInTheDocument();

    setTimeoutSpy.mockRestore();
    clearTimeoutSpy.mockRestore();
  });
});
