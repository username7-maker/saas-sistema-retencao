import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AIAssistantPanel } from "../components/common/AIAssistantPanel";

describe("AIAssistantPanel", () => {
  it("shows the standardized transparency contract", () => {
    render(
      <MemoryRouter>
        <AIAssistantPanel
          assistant={{
            summary: "Ana entrou na fila por risco alto.",
            why_it_matters: "Sem acao hoje, a recuperacao fica mais dificil.",
            next_best_action: "Abrir o perfil e fazer contato hoje.",
            suggested_message: "Oi Ana, quero te ajudar a reorganizar sua rotina desta semana.",
            evidence: ["10 dias sem check-in", "sem contato recente"],
            provider: "system",
            mode: "rule_based",
            fallback_used: true,
            manual_required: true,
            confidence_label: "Alta",
            recommended_channel: "WhatsApp",
            cta_target: "/assessments/members/member-1?tab=contexto",
            cta_label: "Abrir perfil 360",
          }}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText("Estado operacional")).toBeInTheDocument();
    expect(screen.getAllByText("Sistema")).toHaveLength(2);
    expect(screen.getAllByText("Baseado em regras")).toHaveLength(2);
    expect(screen.getByText("WhatsApp")).toBeInTheDocument();
    expect(screen.getByText("Alta")).toBeInTheDocument();
    expect(screen.getByText("O sistema esta em fallback e a acao ainda exige supervisao humana.")).toBeInTheDocument();
    expect(screen.getByText("Fallback ativo")).toBeInTheDocument();
    expect(screen.getByText("Supervisao humana")).toBeInTheDocument();
  });
});
