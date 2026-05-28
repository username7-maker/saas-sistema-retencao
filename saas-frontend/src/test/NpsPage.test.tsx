import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { NpsPage } from "../pages/nps/NpsPage";
import { npsService } from "../services/npsService";

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    user: { id: "owner-1", full_name: "Owner Teste", role: "owner" },
  }),
}));

vi.mock("../services/npsService", () => ({
  npsService: {
    evolution: vi.fn(),
    detractors: vi.fn(),
    dispatch: vi.fn(),
    getDispatchStatus: vi.fn(),
  },
}));

vi.mock("../services/taskService", () => ({
  taskService: {
    createTask: vi.fn(),
  },
}));

vi.mock("../components/charts/LineSeriesChart", () => ({
  LineSeriesChart: () => <div>Chart mock</div>,
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
        <NpsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("NpsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(npsService.evolution).mockResolvedValue([]);
    vi.mocked(npsService.detractors).mockResolvedValue([]);
    vi.mocked(npsService.dispatch).mockResolvedValue({
      message: "Disparo de NPS enfileirado.",
      job_id: "job-1",
      job_type: "nps_dispatch",
      status: "pending",
    });
  });

  it("explains the empty NPS state without making the module look broken", async () => {
    renderPage();

    expect(await screen.findByText("Sem respostas NPS ainda")).toBeInTheDocument();
    expect(screen.getByText(/O módulo está operacional/i)).toBeInTheDocument();
    expect(screen.getByText("Nenhum detrator nos últimos 30 dias.")).toBeInTheDocument();
  });

  it("queues an NPS dispatch for authorized users", async () => {
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "Disparar pesquisa NPS" }));

    await waitFor(() => {
      expect(npsService.dispatch).toHaveBeenCalled();
    });
  });
});
