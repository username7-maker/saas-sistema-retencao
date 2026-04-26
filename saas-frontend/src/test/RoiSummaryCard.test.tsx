import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RoiSummaryCard } from "../components/dashboard/RoiSummaryCard";
import { api } from "../services/api";

vi.mock("../services/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

function renderCard() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <RoiSummaryCard />
    </QueryClientProvider>,
  );
}

describe("RoiSummaryCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("uses an honest empty state when there is no confirmed automation ROI", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        period_days: 30,
        total_automated: 0,
        reengaged_count: 0,
        reengagement_rate: 0,
        preserved_revenue: 0,
      },
    });

    renderCard();

    expect(await screen.findByText("ROI das Automacoes")).toBeInTheDocument();
    expect(screen.getByText(/Sem resultados reais de automacao registrados/i)).toBeInTheDocument();
    expect(screen.queryByText(/automacoes estao ativas/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/tempo medio para o primeiro reengajamento/i)).not.toBeInTheDocument();
  });
});
