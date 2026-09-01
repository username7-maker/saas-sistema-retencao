import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AssessmentRegistrationComposer } from "../components/assessments/AssessmentRegistrationComposer";
import { assessmentService } from "../services/assessmentService";


function renderComposer(options: { editingAssessmentId?: string; onSaved?: (assessmentId: string) => void } = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AssessmentRegistrationComposer
        memberId="member-1"
        member={{
          full_name: "Aluno Slaughter",
          birthdate: "2011-01-01",
          sex_for_clinical_calculation: "male",
          height_cm: 170,
        }}
        initialMode="manual_anthropometry"
        editingAssessmentId={options.editingAssessmentId}
        onSaved={options.onSaved}
      />
    </QueryClientProvider>,
  );
}


describe("AssessmentRegistrationComposer", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.sessionStorage.clear();
    vi.spyOn(assessmentService, "anthropometryProtocols").mockResolvedValue([
      {
        key: "slaughter_1988_boys_black_white_6_17",
        label: "Slaughter et al. (1988), Meninos negros ou brancos, 6-17 anos",
        sex: "male",
        age_min: 6,
        age_max: 17,
        required_fields: ["skinfold_triceps_mm", "skinfold_subscapular_mm"],
        required_choice_fields: ["anthropometry_ethnicity", "anthropometry_maturity"],
        supported: true,
      },
    ]);
  });

  it("shows Slaughter population choices in the no-bioimpedance flow", async () => {
    renderComposer();

    expect(await screen.findByLabelText("Grupo etnico usado na formula")).toBeInTheDocument();
    expect(screen.getByLabelText("Estagio maturacional")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Branco" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Asiatico" })).not.toBeInTheDocument();
  });

  it("adds Poortmans measurements for an eligible white child without duplicating fields", async () => {
    renderComposer();
    await screen.findByLabelText("Grupo etnico usado na formula");

    fireEvent.click(screen.getByRole("checkbox", { name: /calcular massa muscular/i }));
    fireEvent.change(screen.getByLabelText("Grupo etnico usado na formula"), { target: { value: "white" } });

    expect(screen.getByLabelText("Braco direito relaxado - tentativa 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Coxa direita - tentativa 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Panturrilha direita - tentativa 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Dobra coxa - tentativa 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Dobra panturrilha - tentativa 1")).toBeInTheDocument();
    expect(screen.getAllByLabelText("Dobra tricipital - tentativa 1")).toHaveLength(1);
  });

  it("restores the no-bioimpedance draft after the form is reloaded", async () => {
    const firstRender = renderComposer();
    await screen.findByLabelText("Grupo etnico usado na formula");

    fireEvent.change(screen.getByLabelText("Peso"), { target: { value: "82,3" } });
    fireEvent.change(screen.getByLabelText("Grupo etnico usado na formula"), { target: { value: "black" } });
    fireEvent.change(screen.getByLabelText("Estagio maturacional"), { target: { value: "pubertal" } });
    fireEvent.change(screen.getByLabelText("Dobra tricipital - tentativa 1"), { target: { value: "12,5" } });
    fireEvent.change(screen.getByLabelText("Observacoes"), { target: { value: "Aluno em jejum." } });

    await waitFor(() => expect(window.sessionStorage.length).toBe(1));
    firstRender.unmount();
    renderComposer();

    expect(await screen.findByLabelText("Peso")).toHaveValue("82,3");
    expect(screen.getByLabelText("Grupo etnico usado na formula")).toHaveValue("black");
    expect(screen.getByLabelText("Estagio maturacional")).toHaveValue("pubertal");
    expect(screen.getByLabelText("Dobra tricipital - tentativa 1")).toHaveValue("12,5");
    expect(screen.getByLabelText("Observacoes")).toHaveValue("Aluno em jejum.");
  });

  it("shows the backend-controlled TMB origin in the calculated preview", async () => {
    vi.spyOn(assessmentService, "previewAnthropometry").mockResolvedValue({
      assessment_method: "manual_anthropometry",
      record_origin: "cordex",
      protocol: { key: "slaughter_1988_boys_black_white_6_17", label: "Slaughter" },
      formula_version: "schofield_hw_1985",
      calculation_hash: "hash-1",
      results: { basal_metabolic_rate: 1512 },
      indicator_origins: { basal_metabolic_rate: "schofield_hw_1985" },
      snapshot: { flags: [] },
    });
    renderComposer();

    fireEvent.change(await screen.findByLabelText("Peso"), { target: { value: "50" } });
    fireEvent.change(screen.getByLabelText("Grupo etnico usado na formula"), { target: { value: "white" } });
    fireEvent.change(screen.getByLabelText("Estagio maturacional"), { target: { value: "pubertal" } });
    fireEvent.change(screen.getByLabelText("Dobra tricipital - tentativa 1"), { target: { value: "12" } });
    fireEvent.change(screen.getByLabelText("Dobra tricipital - tentativa 2"), { target: { value: "12" } });
    fireEvent.change(screen.getByLabelText("Dobra subescapular - tentativa 1"), { target: { value: "10" } });
    fireEvent.change(screen.getByLabelText("Dobra subescapular - tentativa 2"), { target: { value: "10" } });
    fireEvent.click(screen.getByRole("button", { name: "Calcular previa" }));

    expect(await screen.findByText("1512 kcal/dia")).toBeInTheDocument();
    expect(screen.getByText("Origem: TMB por Schofield")).toBeInTheDocument();
  });

  it("loads original attempts for editing and sends only measured inputs with the concurrency token", async () => {
    const updatedAt = "2026-08-28T13:19:00Z";
    vi.spyOn(assessmentService, "getAnthropometry").mockResolvedValue({
      id: "anthropometry-1",
      assessment_date: "2026-08-28T13:18:00Z",
      updated_at: updatedAt,
      assessment_method: "manual_anthropometry",
      measurement_protocol: "slaughter_1988_boys_black_white_6_17",
      observations: "Medida original",
      anthropometry_snapshot_json: {
        protocol: { key: "slaughter_1988_boys_black_white_6_17" },
        inputs: {
          sex_used_for_formula: "male",
          age_used_for_formula: 15,
          height_used_for_formula: "170.0",
          weight_used_for_formula: "60.0",
          anthropometry_ethnicity: "white",
          anthropometry_maturity: "pubertal",
          calculate_muscle_mass: false,
        },
        measurements: {
          height_cm: { attempts: [170, 170], consolidated_value: 170 },
          weight_kg: { attempts: [60, 60], consolidated_value: 60 },
          skinfold_triceps_mm: { attempts: [12.1, 12.3], consolidated_value: 12.2 },
          skinfold_subscapular_mm: { attempts: [10, 10], consolidated_value: 10 },
        },
      },
    } as unknown as Awaited<ReturnType<typeof assessmentService.getAnthropometry>>);
    vi.spyOn(assessmentService, "previewAnthropometry").mockResolvedValue({
      assessment_method: "manual_anthropometry",
      record_origin: "cordex",
      protocol: { key: "slaughter_1988_boys_black_white_6_17", label: "Slaughter" },
      formula_version: "anthropometry-v3",
      calculation_hash: "hash-new",
      results: { body_fat_pct: 18, basal_metabolic_rate: 1600 },
      indicator_origins: { basal_metabolic_rate: "schofield_hw_1985" },
      snapshot: { flags: [] },
    });
    const updateSpy = vi.spyOn(assessmentService, "updateAnthropometry").mockResolvedValue({
      id: "anthropometry-1",
      extra_data: { actuar_sync: { sync_status: "manual_sync_required" } },
    } as unknown as Awaited<ReturnType<typeof assessmentService.updateAnthropometry>>);
    const onSaved = vi.fn();

    renderComposer({ editingAssessmentId: "anthropometry-1", onSaved });

    await waitFor(() => expect(screen.getByLabelText("Dobra tricipital - tentativa 1")).toHaveValue("12.1"));
    expect(screen.getByLabelText("Dobra tricipital - tentativa 2")).toHaveValue("12.3");
    expect(screen.getByLabelText("Observacoes")).toHaveValue("Medida original");
    fireEvent.click(screen.getByRole("button", { name: "Calcular previa" }));
    await screen.findByText("1600 kcal/dia");
    fireEvent.click(screen.getByRole("button", { name: "Salvar alteracoes" }));

    await waitFor(() => expect(updateSpy).toHaveBeenCalled());
    expect(updateSpy.mock.calls[0][2]).toEqual(expect.objectContaining({
      expected_updated_at: updatedAt,
      measurements: expect.objectContaining({
        skinfold_triceps_mm: expect.objectContaining({ attempts: [12.1, 12.3] }),
      }),
    }));
    expect(updateSpy.mock.calls[0][2]).not.toHaveProperty("body_fat_pct");
    expect(onSaved).toHaveBeenCalledWith("anthropometry-1");
  });
});
