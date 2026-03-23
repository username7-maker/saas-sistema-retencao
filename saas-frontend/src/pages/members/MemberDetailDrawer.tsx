import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import toast from "react-hot-toast";
import type { Member } from "../../types";
import { QuickActions } from "../../components/common/QuickActions";
import { Badge, Drawer } from "../../components/ui2";
import { lgpdService } from "../../services/lgpdService";
import { memberService } from "../../services/memberService";
import { buildWhatsAppHref, formatPhoneDisplay, normalizeWhatsAppPhone } from "../../utils/whatsapp";
import { RISK_LABELS, RISK_VARIANTS, STATUS_LABELS, STATUS_VARIANTS } from "./memberUtils";

export function MemberDetailDrawer({
  member,
  open,
  onClose,
}: {
  member: Member | null;
  open: boolean;
  onClose: () => void;
}) {
  const [confirmAnonymize, setConfirmAnonymize] = useState(false);
  const [lgpdLoading, setLgpdLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "assessment" | "behavior" | "retention">("overview");

  const { data: onboardingScore } = useQuery({
    queryKey: ["onboarding-score", member?.id],
    queryFn: () => memberService.getOnboardingScore(member!.id),
    enabled: !!member && member.onboarding_status === "active",
  });

  const { data: profile360, isLoading: loadingProfile } = useQuery({
    queryKey: ["profile-360", member?.id],
    queryFn: () => memberService.getProfile360(member!.id),
    enabled: !!member?.id,
    staleTime: 2 * 60 * 1000,
  });

  if (!member) {
    return null;
  }

  const scoreColor = (s: number) => (s >= 70 ? "bg-green-500" : s >= 40 ? "bg-yellow-400" : "bg-red-500");
  const FACTOR_LABELS: Record<string, string> = {
    checkin_frequency: "Frequencia",
    first_assessment: "1a Avaliacao",
    task_completion: "Tarefas",
    consistency: "Consistencia",
    member_response: "Resposta/feedback",
  };
  const normalizedPhone = normalizeWhatsAppPhone(member.phone);
  const phoneDisplay = formatPhoneDisplay(member.phone);
  const whatsappHref = buildWhatsAppHref(member.phone, undefined, member.full_name);

  const handleExportLgpd = async () => {
    setLgpdLoading(true);
    try {
      await lgpdService.exportMemberPdf(member.id);
      toast.success("PDF de dados gerado com sucesso");
    } catch {
      toast.error("Erro ao exportar dados LGPD");
    } finally {
      setLgpdLoading(false);
    }
  };

  const handleAnonymize = async () => {
    setLgpdLoading(true);
    try {
      await lgpdService.anonymizeMember(member.id);
      toast.success("Dados do membro anonimizados");
      setConfirmAnonymize(false);
      onClose();
    } catch {
      toast.error("Erro ao anonimizar membro");
    } finally {
      setLgpdLoading(false);
    }
  };

  const lastCheckin = member.last_checkin_at
    ? new Date(member.last_checkin_at).toLocaleDateString("pt-BR")
    : "Nunca";

  return (
    <Drawer open={open} onClose={onClose} title={member.full_name}>
      <div className="flex gap-0 border-b border-lovable-border px-2">
        {(["overview", "assessment", "behavior", "retention"] as const).map((tab) => {
          const labels = {
            overview: "Visao Geral",
            assessment: "Avaliacao",
            behavior: "Comportamento",
            retention: "Retencao",
          };
          return (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={clsx(
                "-mb-px border-b-2 px-3 py-2.5 text-xs font-semibold transition",
                activeTab === tab
                  ? "border-lovable-primary text-lovable-primary"
                  : "border-transparent text-lovable-ink-muted hover:text-lovable-ink",
              )}
            >
              {labels[tab]}
            </button>
          );
        })}
      </div>

      {activeTab === "overview" && (
        <div className="space-y-4 p-4">
          <div className="flex items-center gap-3">
            <Badge variant={RISK_VARIANTS[member.risk_level]}>
              Risco {RISK_LABELS[member.risk_level]} ({member.risk_score})
            </Badge>
            <Badge variant={STATUS_VARIANTS[member.status]}>{STATUS_LABELS[member.status]}</Badge>
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-lovable-ink-muted">Email</p>
              <p className="font-medium text-lovable-ink">{member.email ?? "-"}</p>
            </div>
            <div>
              <p className="text-lovable-ink-muted">Telefone</p>
              {normalizedPhone && phoneDisplay ? (
                <div className="flex flex-wrap items-center gap-2">
                  <a href={`tel:${normalizedPhone}`} className="font-medium text-lovable-ink hover:text-lovable-primary">
                    {phoneDisplay}
                  </a>
                  {whatsappHref ? (
                    <a
                      href={whatsappHref}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs font-semibold text-lovable-primary hover:underline"
                    >
                      WhatsApp
                    </a>
                  ) : null}
                </div>
              ) : (
                <p className="font-medium text-lovable-ink">-</p>
              )}
            </div>
            <div>
              <p className="text-lovable-ink-muted">Plano</p>
              <p className="font-medium text-lovable-ink">{member.plan_name}</p>
            </div>
            <div>
              <p className="text-lovable-ink-muted">Mensalidade</p>
              <p className="font-medium text-lovable-ink">
                {member.monthly_fee.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
              </p>
            </div>
            <div>
              <p className="text-lovable-ink-muted">Membro desde</p>
              <p className="font-medium text-lovable-ink">{new Date(member.join_date).toLocaleDateString("pt-BR")}</p>
            </div>
            <div>
              <p className="text-lovable-ink-muted">Nascimento</p>
              <p className="font-medium text-lovable-ink">
                {member.birthdate ? new Date(`${member.birthdate}T12:00:00`).toLocaleDateString("pt-BR") : "-"}
              </p>
            </div>
            <div>
              <p className="text-lovable-ink-muted">Ultimo check-in</p>
              <p className="font-medium text-lovable-ink">{lastCheckin}</p>
            </div>
            <div>
              <p className="text-lovable-ink-muted">Fidelidade</p>
              <p className="font-medium text-lovable-ink">{member.loyalty_months} meses</p>
            </div>
            <div>
              <p className="text-lovable-ink-muted">NPS</p>
              <p className="font-medium text-lovable-ink">{member.nps_last_score > 0 ? member.nps_last_score : "-"}</p>
            </div>
          </div>

          <div className="border-t border-lovable-border pt-3">
            <p className="mb-2 text-sm font-semibold text-lovable-ink">Acoes Rapidas</p>
            <QuickActions member={member} />
          </div>

          {onboardingScore && (
            <div className="border-t border-lovable-border pt-3">
              <p className="mb-2 text-sm font-semibold text-lovable-ink">Score de Onboarding</p>
              <div className="mb-3 flex items-center gap-3">
                <div className="h-3 flex-1 overflow-hidden rounded-full bg-lovable-surface-soft">
                  <div
                    className={`h-3 rounded-full transition-all ${scoreColor(onboardingScore.score)}`}
                    style={{ width: `${onboardingScore.score}%` }}
                  />
                </div>
                <span className={`text-sm font-bold ${onboardingScore.score >= 70 ? "text-green-600" : onboardingScore.score >= 40 ? "text-yellow-600" : "text-red-600"}`}>
                  {onboardingScore.score}
                </span>
              </div>
              <div className="space-y-1.5">
                {(Object.entries(onboardingScore.factors) as [string, number][]).map(([key, val]) => (
                  <div key={key} className="flex items-center gap-2 text-xs">
                    <span className="w-28 shrink-0 text-lovable-ink-muted">{FACTOR_LABELS[key] ?? key}</span>
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-lovable-surface-soft">
                      <div
                        className={`h-1.5 rounded-full ${scoreColor(val)}`}
                        style={{ width: `${val}%` }}
                      />
                    </div>
                    <span className="w-6 text-right text-lovable-ink-muted">{val}</span>
                  </div>
                ))}
              </div>
              <p className="mt-2 text-xs text-lovable-ink-muted">
                {onboardingScore.checkin_count} check-ins · {onboardingScore.completed_tasks}/{onboardingScore.total_tasks} tarefas · dia {onboardingScore.days_since_join}
              </p>
            </div>
          )}

          <div className="border-t border-lovable-border pt-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">LGPD</p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => void handleExportLgpd()}
                disabled={lgpdLoading}
                className="rounded-full border border-lovable-border px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted hover:bg-lovable-surface-soft disabled:opacity-50"
              >
                Exportar dados
              </button>
              {!confirmAnonymize ? (
                <button
                  type="button"
                  onClick={() => setConfirmAnonymize(true)}
                  disabled={lgpdLoading}
                  className="rounded-full border border-lovable-danger/40 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-lovable-danger hover:bg-lovable-danger/5 disabled:opacity-50"
                >
                  Anonimizar
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <p className="text-xs text-lovable-danger">Confirmar anonimiazacao?</p>
                  <button
                    type="button"
                    onClick={() => void handleAnonymize()}
                    disabled={lgpdLoading}
                    className="rounded-full bg-lovable-danger px-3 py-1 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50"
                  >
                    {lgpdLoading ? "..." : "Confirmar"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmAnonymize(false)}
                    className="text-xs text-lovable-ink-muted hover:text-lovable-ink"
                  >
                    Cancelar
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === "assessment" && (
        <div className="space-y-3 p-4">
          {loadingProfile || profile360 === undefined ? (
            <p className="text-sm text-lovable-ink-muted">Carregando...</p>
          ) : (() => {
            const profile = (profile360 ?? {}) as Record<string, any>;
            const assess = profile.assessment ?? null;
            const next = assess?.next_assessment ?? null;
            const latest = assess?.latest ?? profile.latest_assessment ?? null;
            const deltas = assess?.evolution?.deltas ?? null;

            return (
              <>
                <div className={clsx("rounded-xl border p-3", next?.overdue ? "border-red-200 bg-red-50" : "border-lovable-border")}>
                  <p className="mb-1 text-[10px] font-semibold uppercase text-lovable-ink-muted">Proxima avaliacao</p>
                  <p className={clsx("text-sm font-bold", next?.overdue ? "text-red-600" : "text-lovable-ink")}>
                    {next?.overdue
                      ? `Atrasada ${typeof next?.days_until_due === "number" ? Math.abs(next.days_until_due) : "?"} dias`
                      : next?.due_date
                        ? new Date(next.due_date).toLocaleDateString("pt-BR")
                        : latest?.next_assessment_due
                          ? new Date(latest.next_assessment_due).toLocaleDateString("pt-BR")
                          : "-"}
                  </p>
                </div>

                {latest ? (
                  <div className="rounded-xl border border-lovable-border p-3">
                    <p className="mb-2 text-[10px] font-semibold uppercase text-lovable-ink-muted">Ultima avaliacao</p>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      {[
                        { label: "Peso", value: latest?.weight_kg != null ? `${latest.weight_kg}kg` : "-" },
                        { label: "Gordura", value: latest?.body_fat_pct != null ? `${latest.body_fat_pct}%` : "-" },
                        { label: "Massa Magra", value: latest?.lean_mass_kg != null ? `${latest.lean_mass_kg}kg` : "-" },
                      ].map((item) => (
                        <div key={item.label}>
                          <p className="text-[10px] text-lovable-ink-muted">{item.label}</p>
                          <p className="text-sm font-bold text-lovable-ink">{item.value}</p>
                        </div>
                      ))}
                    </div>
                    {latest?.assessment_date ? (
                      <p className="mt-2 text-[10px] text-lovable-ink-muted">
                        {new Date(latest.assessment_date).toLocaleDateString("pt-BR")}
                      </p>
                    ) : null}
                  </div>
                ) : null}

                {deltas ? (
                  <div className="rounded-xl border border-lovable-border p-3">
                    <p className="mb-2 text-[10px] font-semibold uppercase text-lovable-ink-muted">Evolucao desde o inicio</p>
                    {[
                      { label: "Peso", key: "weight_kg", unit: "kg", lowerIsBetter: false },
                      { label: "Gordura", key: "body_fat_pct", unit: "%", lowerIsBetter: true },
                      { label: "Massa Magra", key: "lean_mass_kg", unit: "kg", lowerIsBetter: false },
                    ].map(({ label, key, unit, lowerIsBetter }) => {
                      const val = deltas?.[key];
                      if (val == null) return null;
                      const positive = val > 0;
                      const good = lowerIsBetter ? !positive : positive;
                      return (
                        <div key={key} className="flex items-center justify-between border-b border-lovable-border py-1 last:border-0">
                          <span className="text-xs text-lovable-ink-muted">{label}</span>
                          <span className={clsx("text-xs font-bold", good ? "text-green-600" : "text-red-500")}>
                            {positive ? "+" : ""}{val}{unit}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ) : null}
              </>
            );
          })()}
        </div>
      )}

      {activeTab === "behavior" && (
        <div className="space-y-3 p-4">
          {loadingProfile || profile360 === undefined ? (
            <p className="text-sm text-lovable-ink-muted">Carregando...</p>
          ) : (() => {
            const profile = (profile360 ?? {}) as Record<string, any>;
            const beh = profile.behavior ?? null;
            const series: number[] = Array.isArray(beh?.weekly_series) ? beh.weekly_series : [];

            return (
              <>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: "Check-ins 90d", value: beh?.total_checkins_90d ?? "-" },
                    { label: "Media semanal", value: beh?.avg_weekly != null ? `${beh.avg_weekly}x/sem` : "-" },
                    { label: "Consistencia", value: beh?.consistency_pct != null ? `${beh.consistency_pct}%` : "-" },
                    { label: "Turno favorito", value: beh?.preferred_shift ?? member.preferred_shift ?? "-" },
                  ].map((item) => (
                    <div key={item.label} className="rounded-xl border border-lovable-border p-3">
                      <p className="text-[10px] text-lovable-ink-muted">{item.label}</p>
                      <p className="text-sm font-bold text-lovable-ink">{String(item.value)}</p>
                    </div>
                  ))}
                </div>

                {series.length > 0 ? (
                  <div className="rounded-xl border border-lovable-border p-3">
                    <p className="mb-2 text-[10px] font-semibold uppercase text-lovable-ink-muted">
                      Treinos por semana (ultimas {series.length} semanas)
                    </p>
                    <div className="flex h-10 items-end gap-1">
                      {series.map((value, index) => {
                        const max = Math.max(...series, 1);
                        const height = Math.round((value / max) * 100);
                        return (
                          <div
                            key={index}
                            className="flex-1 rounded-sm bg-lovable-primary/30 transition-all"
                            style={{ height: `${height}%`, minHeight: value > 0 ? "2px" : "0" }}
                            title={`${value} treino${value !== 1 ? "s" : ""}`}
                          />
                        );
                      })}
                    </div>
                  </div>
                ) : null}
              </>
            );
          })()}
        </div>
      )}

      {activeTab === "retention" && (
        <div className="space-y-3 p-4">
          {loadingProfile || profile360 === undefined ? (
            <p className="text-sm text-lovable-ink-muted">Carregando...</p>
          ) : (() => {
            const profile = (profile360 ?? {}) as Record<string, any>;
            const ret = profile.retention ?? null;
            const ai = profile.ai_engine ?? null;
            const urgency = ret?.urgency ?? null;
            const isCritical = urgency === "vip_em_risco" || urgency === "critico";
            const isWarning = urgency === "atencao";

            return (
              <>
                <div
                  className={clsx(
                    "rounded-xl border p-3",
                    isCritical ? "border-red-200 bg-red-50" : isWarning ? "border-yellow-200 bg-yellow-50" : "border-green-200 bg-green-50",
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <p className="text-[10px] font-semibold uppercase text-lovable-ink-muted">Urgencia</p>
                      <p className="text-sm font-bold capitalize text-lovable-ink">{urgency ? urgency.replace(/_/g, " ") : "-"}</p>
                    </div>
                    {ret?.churn_type_label ? (
                      <span className="rounded-full border border-lovable-border bg-white/70 px-2 py-1 text-[10px] font-semibold text-lovable-ink">
                        {ret.churn_type_label}
                      </span>
                    ) : null}
                  </div>
                </div>

                {typeof ret?.forecast_60d === "number" && ret.forecast_60d >= 0 && ret.forecast_60d <= 100 ? (
                  <div className="rounded-xl border border-lovable-border p-3">
                    <p className="mb-2 text-[10px] font-semibold uppercase text-lovable-ink-muted">
                      Probabilidade de permanencia (60d)
                    </p>
                    <div className="flex items-center gap-3">
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-lovable-surface-soft">
                        <div
                          className={clsx(
                            "h-2 rounded-full transition-all",
                            ret.forecast_60d >= 60 ? "bg-green-500" : ret.forecast_60d >= 40 ? "bg-yellow-400" : "bg-red-500",
                          )}
                          style={{ width: `${ret.forecast_60d}%` }}
                        />
                      </div>
                      <span
                        className={clsx(
                          "text-sm font-bold",
                          ret.forecast_60d >= 60 ? "text-green-600" : ret.forecast_60d >= 40 ? "text-yellow-600" : "text-red-600",
                        )}
                      >
                        {ret.forecast_60d}%
                      </span>
                    </div>
                  </div>
                ) : null}

                {ai?.next_best_action ? (
                  <div className="rounded-xl border border-lovable-primary/30 bg-lovable-primary-soft/20 p-3">
                    <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-lovable-primary">
                      ✦ IA - Proxima acao recomendada
                    </p>
                    <p className="text-xs text-lovable-ink">{ai.next_best_action}</p>
                  </div>
                ) : null}

                {!ret && !ai ? (
                  <p className="text-sm text-lovable-ink-muted">
                    Dados de retencao ainda nao disponiveis para este aluno.
                  </p>
                ) : null}
              </>
            );
          })()}
        </div>
      )}
    </Drawer>
  );
}
