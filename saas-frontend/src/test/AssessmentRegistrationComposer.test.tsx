import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
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

  it("adds Lee measurements without duplicating fields already required by the protocol", async () => {
    renderComposer();
    await screen.findByLabelText("Grupo etnico usado na formula");

    fireEvent.click(screen.getByRole("checkbox", { name: /calcular massa muscular/i }));

    expect(screen.getByLabelText("Braco direito relaxado - tentativa 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Coxa direita - tentativa 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Panturrilha direita - tentativa 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Dobra coxa - tentativa 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Dobra panturrilha - tentativa 1")).toBeInTheDocument();
    expect(screen.getAllByLabelText("Dobra tricipital - tentativa 1")).toHaveLength(1);
  });
});
