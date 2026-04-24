import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BodyCompositionReportPage from "../pages/assessments/BodyCompositionReportPage";
import { bodyCompositionService } from "../services/bodyCompositionService";
import type { BodyCompositionReport } from "../types";

vi.mock("../services/bodyCompositionService", () => ({
  bodyCompositionService: {
    getReport: vi.fn(),
    openPdf: vi.fn(),
  },
}));

function makeReport(): BodyCompositionReport {
  return {
    header: {
      member_name: "Erick Bedin",
      gym_name: "AI GYM OS Piloto",
      trainer_name: "Automicai Owner",
      measured_at: "2026-04-14T10:00:00Z",
      age_years: 21,
      sex: "male",
      height_cm: 178,
      weight_kg: 84.5,
    },
    current_evaluation_id: "eval-1",
    previous_evaluation_id: "eval-0",
    reviewed_manually: true,
    parsing_confidence: 0.91,
    data_quality_flags: [],
    primary_cards: [
      { key: "weight", label: "Peso", value: 84.5, unit: "kg", formatted_value: "84.5 kg", delta_absolute: -1.2, delta_percent: -1.4, trend: "down" },
      { key: "body_fat_percent", label: "% Gordura corporal", value: 23, unit: "%", formatted_value: "23%", delta_absolute: -1.8, delta_percent: -7.3, trend: "down" },
      { key: "visceral_fat_level", label: "Gordura visceral", value: 9, unit: null, formatted_value: "9", delta_absolute: 0, delta_percent: 0, trend: "stable" },
      { key: "muscle_mass_kg", label: "Massa muscular", value: 35.6, unit: "kg", formatted_value: "35.6 kg", delta_absolute: 0.4, delta_percent: 1.1, trend: "up" },
      { key: "bmi", label: "IMC", value: 26.7, unit: null, formatted_value: "26.7", delta_absolute: -0.3, delta_percent: -1.1, trend: "down" },
      { key: "bmr", label: "Metabolismo basal", value: 1880, unit: "kcal", formatted_value: "1880 kcal", delta_absolute: 32, delta_percent: 1.7, trend: "up" },
    ],
    composition_metrics: [
      { key: "water", label: "Agua corporal", value: 43.3, unit: "kg", formatted_value: "43.3 kg", reference_min: 39, reference_max: 48, status: "adequate", hint: "Dentro da faixa" },
      { key: "protein", label: "Proteina", value: 17.7, unit: "kg", formatted_value: "17.7 kg", reference_min: 16, reference_max: 19, status: "adequate", hint: null },
    ],
    muscle_fat_metrics: [
      { key: "weight", label: "Peso", value: 84.5, unit: "kg", formatted_value: "84.5 kg", reference_min: 65, reference_max: 80, status: "high", hint: null },
      { key: "skeletal_muscle", label: "Musculo esqueletico", value: 35.6, unit: "kg", formatted_value: "35.6 kg", reference_min: 28, reference_max: 38, status: "adequate", hint: null },
      { key: "fat_mass", label: "Gordura corporal", value: 19.4, unit: "kg", formatted_value: "19.4 kg", reference_min: 8, reference_max: 16, status: "high", hint: null },
    ],
    risk_metrics: [
      { key: "bmi", label: "IMC", value: 26.7, unit: null, formatted_value: "26.7", reference_min: 18.5, reference_max: 24.9, status: "high", hint: "Acompanhamento operacional" },
      { key: "whr", label: "Relacao cintura-quadril", value: 0.88, unit: null, formatted_value: "0.88", reference_min: 0.75, reference_max: 0.9, status: "adequate", hint: null },
    ],
    goal_metrics: [
      { key: "target_weight", label: "Peso-alvo", value: 78, unit: "kg", formatted_value: "78 kg", reference_min: null, reference_max: null, status: "unknown", hint: null },
      { key: "fat_control", label: "Controle de gordura", value: -6.5, unit: "kg", formatted_value: "-6.5 kg", reference_min: null, reference_max: null, status: "unknown", hint: null },
    ],
    comparison_rows: [
      {
        key: "weight",
        label: "Peso",
        unit: "kg",
        previous_value: 85.7,
        current_value: 84.5,
        previous_formatted: "85.7 kg",
        current_formatted: "84.5 kg",
        difference_absolute: -1.2,
        difference_percent: -1.4,
        trend: "down",
      },
    ],
    history_series: [
      {
        key: "weight",
        label: "Peso",
        unit: "kg",
        points: [
          { evaluation_id: "eval-0", measured_at: "2026-03-10T10:00:00Z", evaluation_date: "2026-03-10", value: 85.7 },
          { evaluation_id: "eval-1", measured_at: "2026-04-14T10:00:00Z", evaluation_date: "2026-04-14", value: 84.5 },
        ],
      },
    ],
    insights: [
      {
        key: "fat_down_muscle_stable",
        title: "Reducao de gordura com preservacao muscular",
        message: "Houve reducao de gordura corporal com manutencao de massa muscular nas ultimas avaliacoes.",
        tone: "positive",
        reasons: ["body_fat_percent_down", "muscle_mass_stable"],
      },
    ],
    teacher_notes: "Manter estrategia de treino de forca e ajustes de rotina.",
    methodological_note:
      "Comparacoes historicas sao mais confiaveis quando as medicoes sao feitas em condicoes semelhantes de hidratacao, alimentacao, exercicio e horario.",
    segmental_analysis_available: false,
  };
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/assessments/members/member-1/body-composition/eval-1/report"]}>
        <Routes>
          <Route path="/assessments/members/:memberId/body-composition/:evaluationId/report" element={<BodyCompositionReportPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("BodyCompositionReportPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    if (!("ResizeObserver" in globalThis)) {
      class ResizeObserverMock {
        observe() {}
        unobserve() {}
        disconnect() {}
      }
      vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    }
    vi.mocked(bodyCompositionService.getReport).mockResolvedValue(makeReport());
  });

  it("renders the premium report with metric cards and export actions", async () => {
    renderPage();

    expect(await screen.findByText("Erick Bedin")).toBeInTheDocument();
    expect(screen.getByText("Relatorio premium pronto")).toBeInTheDocument();
    expect(screen.getByText("% Gordura corporal")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Resumo do aluno" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Relatorio tecnico" })).toBeInTheDocument();
    expect(screen.getByText("Reducao de gordura com preservacao muscular")).toBeInTheDocument();
  });

  it("opens the student pdf through the authenticated service", async () => {
    vi.mocked(bodyCompositionService.openPdf).mockResolvedValue(undefined);
    const windowOpenSpy = vi.spyOn(window, "open").mockReturnValue({ location: { href: "" }, close: vi.fn() } as unknown as Window);

    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "Resumo do aluno" }));

    await waitFor(() => {
      expect(bodyCompositionService.openPdf).toHaveBeenCalledWith("member-1", "eval-1", "summary", expect.anything());
    });

    windowOpenSpy.mockRestore();
  });
});
