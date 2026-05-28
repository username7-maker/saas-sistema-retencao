import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GoalsPage } from "../pages/goals/GoalsPage";
import { goalService } from "../services/goalService";

vi.mock("../services/goalService", () => ({
  goalService: {
    progress: vi.fn(),
    create: vi.fn(),
    delete: vi.fn(),
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
        <GoalsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("GoalsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(goalService.progress).mockResolvedValue([]);
    vi.mocked(goalService.create).mockResolvedValue({
      id: "goal-1",
      gym_id: "gym-1",
      name: "MRR Maio",
      metric_type: "mrr",
      comparator: "gte",
      target_value: 25000,
      period_start: "2026-05-01",
      period_end: "2026-05-31",
      alert_threshold_pct: 80,
      is_active: true,
      notes: null,
      created_at: "2026-05-01T00:00:00Z",
      updated_at: "2026-05-01T00:00:00Z",
    });
  });

  it("shows an honest empty state when no goals are configured", async () => {
    renderPage();

    expect(await screen.findByText("Nenhuma meta cadastrada ainda.")).toBeInTheDocument();
    expect(screen.getByText(/Crie a primeira meta para começar/i)).toBeInTheDocument();
  });

  it("creates a goal using the existing goals contract", async () => {
    renderPage();

    fireEvent.change(await screen.findByPlaceholderText("Nome da meta"), { target: { value: "MRR Maio" } });
    fireEvent.change(screen.getByDisplayValue("MRR"), { target: { value: "mrr" } });
    fireEvent.change(screen.getByDisplayValue("Maior ou igual (>=)"), { target: { value: "gte" } });

    const numericInputs = screen.getAllByRole("spinbutton");
    fireEvent.change(numericInputs[0], { target: { value: "25000" } });
    fireEvent.change(numericInputs[1], { target: { value: "75" } });

    const dateInputs = document.querySelectorAll<HTMLInputElement>('input[type="date"]');
    fireEvent.change(dateInputs[0], { target: { value: "2026-05-01" } });
    fireEvent.change(dateInputs[1], { target: { value: "2026-05-31" } });

    fireEvent.click(screen.getByRole("button", { name: "Salvar meta" }));

    await waitFor(() => {
      expect(goalService.create).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "MRR Maio",
          metric_type: "mrr",
          comparator: "gte",
          target_value: 25000,
          period_start: "2026-05-01",
          period_end: "2026-05-31",
          alert_threshold_pct: 75,
        }),
      );
    });
  });
});
