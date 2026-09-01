import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AssessmentRegistrationComposer } from "../components/assessments/AssessmentRegistrationComposer";
import { assessmentService } from "../services/assessmentService";


function renderComposer() {
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
});
