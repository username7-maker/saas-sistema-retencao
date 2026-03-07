import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { Button, Card, CardContent } from "../../components/ui2";
import { salesService } from "../../services/salesService";

const BRL = (value: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(value);

export function SalesBriefingPage() {
  const { leadId = "" } = useParams();
  const navigate = useNavigate();

  const briefQuery = useQuery({
    queryKey: ["sales", "brief", leadId],
    queryFn: () => salesService.getSalesBrief(leadId),
    enabled: Boolean(leadId),
    staleTime: 5 * 60 * 1000,
  });

  const bookingQuery = useQuery({
    queryKey: ["sales", "booking-status", leadId],
    queryFn: () => salesService.getBookingStatus(leadId),
    enabled: Boolean(leadId),
    staleTime: 60 * 1000,
  });

  if (briefQuery.isLoading) {
    return <LoadingPanel text="Montando briefing de vendas..." />;
  }

  if (!briefQuery.data) {
    return <LoadingPanel text="Nao foi possivel carregar o briefing." />;
  }

  const { profile, diagnosis, history, ai_arguments, next_step_recommended } = briefQuery.data;
  const booking = bookingQuery.data;

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">Sales Copilot</p>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Briefing pre-call</h2>
          <p className="mt-1 text-sm text-lovable-ink-muted">
            Lead: {profile.full_name} · Estagio atual: {formatLabel(profile.stage)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" onClick={() => navigate("/crm")}>
            Voltar ao CRM
          </Button>
          <Button variant="primary" onClick={() => navigate(`/vendas/script/${profile.lead_id}`)}>
            Abrir script da call
          </Button>
        </div>
      </header>

      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <CardContent className="space-y-4 pt-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">Perfil do prospect</p>
              <h3 className="mt-1 text-xl font-semibold text-lovable-ink">{profile.gym_name ?? profile.full_name}</h3>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <Info label="Responsavel" value={profile.full_name} />
              <Info label="Porte estimado" value={profile.estimated_members ? `${profile.estimated_members} alunos` : "Nao informado"} />
              <Info label="Mensalidade media" value={profile.avg_monthly_fee ? BRL(profile.avg_monthly_fee) : "Nao informada"} />
              <Info label="Sistema atual" value={profile.current_management_system ?? "Nao detectado"} />
              <Info label="Cidade" value={profile.city ?? "Nao informada"} />
              <Info label="Fonte" value={profile.source} />
            </div>
            {booking?.has_booking ? (
              <div className="rounded-2xl border border-lovable-primary/30 bg-lovable-primary-soft px-4 py-3 text-sm text-lovable-primary">
                Call agendada para {new Date(booking.scheduled_for ?? "").toLocaleString("pt-BR")} via {booking.provider_name ?? "agenda publica"}.
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4 pt-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">Diagnostico resumido</p>
              <h3 className="mt-1 text-xl font-semibold text-lovable-ink">
                {diagnosis.has_diagnosis ? "Numeros do diagnostico gratuito" : "Diagnostico indisponivel"}
              </h3>
            </div>
            {diagnosis.has_diagnosis ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <MetricCard label="Vermelhos" value={String(diagnosis.red_total)} tone="danger" />
                <MetricCard label="Amarelos" value={String(diagnosis.yellow_total)} tone="warning" />
                <MetricCard label="MRR em risco" value={BRL(diagnosis.mrr_at_risk)} />
                <MetricCard label="Perda anual projetada" value={BRL(diagnosis.annual_loss_projection)} />
              </div>
            ) : (
              <p className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-4 text-sm text-lovable-ink-muted">
                {diagnosis.message}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="space-y-4 pt-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">Historico de interacoes</p>
            <h3 className="mt-1 text-xl font-semibold text-lovable-ink">Linha do tempo consolidada</h3>
          </div>
          <div className="space-y-3">
            {history.length === 0 ? (
              <p className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-4 text-sm text-lovable-ink-muted">
                Ainda nao ha interacoes registradas para este lead.
              </p>
            ) : (
              history.map((item, index) => (
                <div key={`${item.kind}-${item.occurred_at}-${index}`} className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-lovable-ink">{item.title}</p>
                    <span className="text-xs text-lovable-ink-muted">
                      {new Date(item.occurred_at).toLocaleString("pt-BR")}
                    </span>
                  </div>
                  {item.detail ? <p className="mt-1 text-sm text-lovable-ink-muted">{item.detail}</p> : null}
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[1fr_0.9fr]">
        <Card>
          <CardContent className="space-y-4 pt-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">Argumentos recomendados pela IA</p>
              <h3 className="mt-1 text-xl font-semibold text-lovable-ink">Como conduzir a conversa</h3>
            </div>
            <div className="space-y-3">
              {ai_arguments.map((argument, index) => (
                <div key={`${argument.title}-${index}`} className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-4">
                  <p className="text-sm font-semibold uppercase tracking-wide text-lovable-primary">
                    Argumento {index + 1}: {argument.title}
                  </p>
                  <p className="mt-2 text-sm text-lovable-ink">{argument.body}</p>
                  <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">Uso</p>
                  <p className="mt-1 text-sm text-lovable-ink-muted">{argument.usage}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4 pt-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">Proximo passo recomendado</p>
              <h3 className="mt-1 text-xl font-semibold text-lovable-ink">Acao sugerida</h3>
            </div>
            <div className="rounded-2xl border border-lovable-border bg-lovable-primary-soft px-4 py-4">
              <p className="text-lg font-semibold capitalize text-lovable-primary">
                {formatLabel(next_step_recommended)}
              </p>
              <p className="mt-2 text-sm text-lovable-ink-muted">
                Use este direcionamento como default, mas ajuste conforme a call evoluir.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">{label}</p>
      <p className="mt-1 text-sm font-medium text-lovable-ink">{value}</p>
    </div>
  );
}

function MetricCard({ label, value, tone = "neutral" }: { label: string; value: string; tone?: "neutral" | "warning" | "danger" }) {
  const toneClass =
    tone === "danger"
      ? "border-lovable-danger/30 bg-lovable-danger/10 text-lovable-danger"
      : tone === "warning"
        ? "border-lovable-warning/30 bg-lovable-warning/10 text-lovable-warning"
        : "border-lovable-border bg-lovable-surface-soft text-lovable-ink";

  return (
    <div className={`rounded-2xl border px-4 py-4 ${toneClass}`}>
      <p className="text-xs font-semibold uppercase tracking-wide">{label}</p>
      <p className="mt-2 text-2xl font-bold">{value}</p>
    </div>
  );
}


function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}
