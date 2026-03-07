import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { useNavigate, useParams } from "react-router-dom";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { Button, Card, CardContent, Dialog, FormField, Textarea } from "../../components/ui2";
import { salesService } from "../../services/salesService";

export function CallScriptPage() {
  const { leadId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeQuickReply, setActiveQuickReply] = useState("");
  const [interestOpen, setInterestOpen] = useState(false);
  const [lostOpen, setLostOpen] = useState(false);
  const [lostReason, setLostReason] = useState("");

  const briefQuery = useQuery({
    queryKey: ["sales", "brief", leadId],
    queryFn: () => salesService.getSalesBrief(leadId),
    enabled: Boolean(leadId),
    staleTime: 5 * 60 * 1000,
  });

  const scriptQuery = useQuery({
    queryKey: ["sales", "script", leadId],
    queryFn: () => salesService.getCallScript(leadId),
    enabled: Boolean(leadId),
    staleTime: 5 * 60 * 1000,
  });

  const eventMutation = useMutation({
    mutationFn: (payload: Parameters<typeof salesService.createCallEvent>[1]) => salesService.createCallEvent(leadId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["sales", "brief", leadId] });
      void queryClient.invalidateQueries({ queryKey: ["sales", "script", leadId] });
      void queryClient.invalidateQueries({ queryKey: ["crm", "leads"] });
    },
    onError: () => toast.error("Nao foi possivel registrar o evento da call."),
  });

  if (briefQuery.isLoading || scriptQuery.isLoading) {
    return <LoadingPanel text="Montando script da call..." />;
  }

  if (!briefQuery.data || !scriptQuery.data) {
    return <LoadingPanel text="Nao foi possivel carregar o script da call." />;
  }

  const brief = briefQuery.data;
  const script = scriptQuery.data;

  async function handleQuickObjection(type: "preco" | "sistema" | "tempo") {
    setActiveQuickReply(type);
    await eventMutation.mutateAsync({
      event_type: `objection_${type}`,
      label: `Objeção: ${type}`,
      details: { quick_response: script.quick_responses[type] },
    });
    toast.success("Resposta rapida registrada na call.");
  }

  async function handleInterest(nextStep: "proposal_requested" | "interest_confirmed" | "close_now") {
    await eventMutation.mutateAsync({
      event_type: nextStep,
      label: "Interesse confirmado",
      next_step: nextStep,
    });
    setInterestOpen(false);
    toast.success(nextStep === "proposal_requested" ? "Proposta sera enviada em background." : "Proximo passo registrado.");
  }

  async function handleLost() {
    await eventMutation.mutateAsync({
      event_type: "lost",
      label: "Lead perdido",
      lost_reason: lostReason,
      details: { lost_reason: lostReason },
    });
    setLostOpen(false);
    setLostReason("");
    toast.success("Lead marcado como perdido.");
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">Call Assist</p>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Script dinamico da call</h2>
          <p className="mt-1 text-sm text-lovable-ink-muted">
            Lead: {brief.profile.full_name} · Estagio: {formatLabel(brief.profile.stage)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" onClick={() => navigate(`/vendas/briefing/${leadId}`)}>
            Voltar ao briefing
          </Button>
          <Button variant="primary" onClick={() => setInterestOpen(true)}>
            Interesse confirmado
          </Button>
          <Button variant="danger" onClick={() => setLostOpen(true)}>
            Perdido
          </Button>
        </div>
      </header>

      <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <Card>
          <CardContent className="space-y-5 pt-5">
            <Section title="Abertura (30 segundos)" content={script.opening} />
            <ListSection title="Qualificacao (2 minutos)" items={script.qualification_questions} />
            <ListSection title="Apresentacao (5 minutos)" items={script.presentation_points} />
            <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">Fechamento</p>
              <p className="mt-2 text-sm text-lovable-ink">{script.closing}</p>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardContent className="space-y-4 pt-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">Acoes rapidas</p>
                <h3 className="mt-1 text-xl font-semibold text-lovable-ink">Tratamento de objecoes</h3>
              </div>
              <div className="grid gap-2">
                <Button variant="secondary" onClick={() => void handleQuickObjection("preco")}>
                  Objeção: preço
                </Button>
                <Button variant="secondary" onClick={() => void handleQuickObjection("sistema")}>
                  Objeção: já tem sistema
                </Button>
                <Button variant="secondary" onClick={() => void handleQuickObjection("tempo")}>
                  Objeção: sem tempo
                </Button>
              </div>
              {activeQuickReply ? (
                <div className="rounded-2xl border border-lovable-primary/30 bg-lovable-primary-soft px-4 py-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-lovable-primary">Resposta sugerida</p>
                  <p className="mt-2 text-sm text-lovable-ink">
                    {script.quick_responses[activeQuickReply]}
                  </p>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-4 pt-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">Objecoes conhecidas</p>
                <h3 className="mt-1 text-xl font-semibold text-lovable-ink">Ja detectadas para este lead</h3>
              </div>
              {script.objections.length === 0 ? (
                <p className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-4 text-sm text-lovable-ink-muted">
                  Nenhuma objeção registrada ate aqui.
                </p>
              ) : (
                script.objections.map((item, index) => (
                  <div key={`${item.summary}-${index}`} className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-4">
                    <p className="text-sm font-semibold text-lovable-ink">{item.summary}</p>
                    <p className="mt-2 text-sm text-lovable-ink-muted">{item.response_text}</p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <Dialog open={interestOpen} onClose={() => setInterestOpen(false)} title="Registrar proximo passo">
        <div className="space-y-3">
          <Button className="w-full" onClick={() => void handleInterest("proposal_requested")}>
            Enviar proposta
          </Button>
          <Button className="w-full" variant="secondary" onClick={() => void handleInterest("interest_confirmed")}>
            Agendar demo
          </Button>
          <Button className="w-full" variant="ghost" onClick={() => void handleInterest("close_now")}>
            Fechar agora
          </Button>
        </div>
      </Dialog>

      <Dialog open={lostOpen} onClose={() => setLostOpen(false)} title="Registrar perda do lead">
        <div className="space-y-4">
          <FormField label="Motivo da perda" required>
            <Textarea value={lostReason} onChange={(event) => setLostReason(event.target.value)} rows={4} />
          </FormField>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setLostOpen(false)}>
              Cancelar
            </Button>
            <Button variant="danger" onClick={() => void handleLost()} disabled={!lostReason.trim()}>
              Confirmar perdido
            </Button>
          </div>
        </div>
      </Dialog>
    </section>
  );
}

function Section({ title, content }: { title: string; content: string }) {
  return (
    <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">{title}</p>
      <p className="mt-2 text-sm text-lovable-ink">{content}</p>
    </div>
  );
}

function ListSection({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">{title}</p>
      <div className="mt-2 space-y-2">
        {items.map((item, index) => (
          <div key={`${title}-${index}`} className="rounded-xl bg-lovable-surface px-3 py-2 text-sm text-lovable-ink">
            {index + 1}. {item}
          </div>
        ))}
      </div>
    </div>
  );
}


function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}
