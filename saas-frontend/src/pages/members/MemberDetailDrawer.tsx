import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import toast from "react-hot-toast";
import type { Member } from "../../types";
import { QuickActions } from "../../components/common/QuickActions";
import { Badge, Drawer } from "../../components/ui2";
import { useAuth } from "../../hooks/useAuth";
import { lgpdService } from "../../services/lgpdService";
import { memberService } from "../../services/memberService";
import { canAnonymizeLgpd, canExportLgpd } from "../../utils/roleAccess";
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
  const { user } = useAuth();
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

  const { data: assessmentSummary, isLoading: loadingSummary } = useQuery({
    queryKey: ["assessment-summary-360", member?.id],
    queryFn: () => memberService.getAssessmentSummary(member!.id),
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
  const canExport = canExportLgpd(user?.role);
  const canAnonymize = canAnonymizeLgpd(user?.role);

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

          {canExport || canAnonymize ? (
            <div className="border-t border-lovable-border pt-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">LGPD</p>
              <div className="flex flex-wrap gap-2">
                {canExport ? (
                  <button
                    type="button"
                    onClick={() => void handleExportLgpd()}
                    disabled={lgpdLoading}
                    className="rounded-full border border-lovable-border px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted hover:bg-lovable-surface-soft disabled:opacity-50"
                  >
                    Exportar dados
                  </button>
                ) : null}
                {canAnonymize ? (
                  !confirmAnonymize ? (
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
                  )
                ) : null}
              </div>
            </div>
          ) : null}
        </div>
      )}

      {activeTab === "assessment" && (
        <div className="space-y-3 p-4">
          {loadingProfile || profile360 === undefined ? (
            <p className="text-sm text-lovable-ink-muted">Carregando...</p>
          ) : (() => {
            const latest = profile360.latest_assessment;

            return (
              <>
                <div className="rounded-xl border border-lovable-border p-3">
                  <p className="mb-1 text-[10px] font-semibold uppercase text-lovable-ink-muted">Proxima avaliacao</p>
                  <p className="text-sm font-bold text-lovable-ink">
                    {latest?.next_assessment_due
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
                        { label: "IMC", value: latest?.bmi != null ? latest.bmi.toFixed(1) : "-" },
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

                {profile360.insight_summary ? (
                  <div className="rounded-xl border border-lovable-primary/30 bg-lovable-primary-soft/20 p-3">
                    <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-lovable-primary">
                      Insight tecnico
                    </p>
                    <p className="text-xs text-lovable-ink">{profile360.insight_summary}</p>
                  </div>
                ) : null}
              </>
            );
          })()}
        </div>
      )}

      {activeTab === "behavior" && (
        <div className="space-y-3 p-4">
          {loadingSummary || assessmentSummary === undefined ? (
            <p className="text-sm text-lovable-ink-muted">Carregando...</p>
          ) : (() => {
            const diagnosis = assessmentSummary.diagnosis;
            const factors = diagnosis.factors;

            return (
              <>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: "Media semanal", value: `${assessmentSummary.recent_weekly_checkins.toFixed(1)}x/sem` },
                    { label: "Meta semanal", value: `${assessmentSummary.target_frequency_per_week}x/sem` },
                    { label: "Dias sem check-in", value: assessmentSummary.days_since_last_checkin ?? "-" },
                    { label: "Gargalo principal", value: diagnosis.primary_bottleneck_label },
                  ].map((item) => (
                    <div key={item.label} className="rounded-xl border border-lovable-border p-3">
                      <p className="text-[10px] text-lovable-ink-muted">{item.label}</p>
                      <p className="text-sm font-bold text-lovable-ink">{String(item.value)}</p>
                    </div>
                  ))}
                </div>

                <div className="rounded-xl border border-lovable-border p-3">
                  <p className="mb-2 text-[10px] font-semibold uppercase text-lovable-ink-muted">Leitura comportamental</p>
                  <p className="text-sm text-lovable-ink">{diagnosis.explanation}</p>
                  <p className="mt-2 text-xs text-lovable-ink-muted">
                    Benchmark atual: {assessmentSummary.benchmark.position_label} · confianca {diagnosis.confidence}
                  </p>
                </div>

                {factors.length > 0 ? (
                  <div className="rounded-xl border border-lovable-border p-3">
                    <p className="mb-2 text-[10px] font-semibold uppercase text-lovable-ink-muted">Fatores observados</p>
                    <div className="space-y-2">
                      {factors.map((factor) => (
                        <div key={factor.key} className="rounded-lg border border-lovable-border px-3 py-2">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-xs font-semibold text-lovable-ink">{factor.label}</p>
                            <span className="text-[11px] font-semibold text-lovable-primary">{factor.score}</span>
                          </div>
                          <p className="mt-1 text-xs text-lovable-ink-muted">{factor.reason}</p>
                        </div>
                      ))}
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
          {loadingSummary || assessmentSummary === undefined ? (
            <p className="text-sm text-lovable-ink-muted">Carregando...</p>
          ) : (() => {
            const retentionProbability = assessmentSummary.forecast.probability_60d;
            const ninetyDayProbability = assessmentSummary.forecast.corrected_probability_90d;
            const statusTone =
              retentionProbability >= 60 ? "border-green-200 bg-green-50" : retentionProbability >= 40 ? "border-yellow-200 bg-yellow-50" : "border-red-200 bg-red-50";

            return (
              <>
                <div
                  className={clsx("rounded-xl border p-3", statusTone)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <p className="text-[10px] font-semibold uppercase text-lovable-ink-muted">Probabilidade de permanencia</p>
                      <p className="text-sm font-bold text-lovable-ink">{retentionProbability}% em 60 dias</p>
                    </div>
                    {assessmentSummary.status ? (
                      <span className="rounded-full border border-lovable-border bg-white/70 px-2 py-1 text-[10px] font-semibold text-lovable-ink">
                        {assessmentSummary.status}
                      </span>
                    ) : null}
                  </div>
                </div>

                <div className="rounded-xl border border-lovable-border p-3">
                  <p className="mb-2 text-[10px] font-semibold uppercase text-lovable-ink-muted">Forecast corrigido</p>
                  <div className="flex items-center gap-3">
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-lovable-surface-soft">
                      <div
                        className={clsx(
                          "h-2 rounded-full transition-all",
                          ninetyDayProbability >= 60 ? "bg-green-500" : ninetyDayProbability >= 40 ? "bg-yellow-400" : "bg-red-500",
                        )}
                        style={{ width: `${ninetyDayProbability}%` }}
                      />
                    </div>
                    <span
                      className={clsx(
                        "text-sm font-bold",
                        ninetyDayProbability >= 60 ? "text-green-600" : ninetyDayProbability >= 40 ? "text-yellow-600" : "text-red-600",
                      )}
                    >
                      {ninetyDayProbability}%
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-lovable-ink-muted">{assessmentSummary.forecast.corrected_summary}</p>
                </div>

                <div className="rounded-xl border border-lovable-border p-3">
                  <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-lovable-primary">Narrativa de retencao</p>
                  <p className="text-xs text-lovable-ink">{assessmentSummary.narratives.retention_summary}</p>
                </div>

                <div className="rounded-xl border border-lovable-primary/30 bg-lovable-primary-soft/20 p-3">
                  <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-lovable-primary">
                    Proxima acao recomendada
                  </p>
                  <p className="text-sm font-semibold text-lovable-ink">{assessmentSummary.next_best_action.title}</p>
                  <p className="mt-1 text-xs text-lovable-ink-muted">{assessmentSummary.next_best_action.reason}</p>
                  <p className="mt-2 text-xs text-lovable-ink">{assessmentSummary.next_best_action.suggested_message}</p>
                </div>

                {assessmentSummary.actions.length > 0 ? (
                  <div className="rounded-xl border border-lovable-primary/30 bg-lovable-primary-soft/20 p-3">
                    <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-lovable-primary">Playbook sugerido</p>
                    <div className="space-y-2">
                      {assessmentSummary.actions.slice(0, 3).map((action) => (
                        <div key={action.key} className="rounded-lg border border-lovable-border bg-white/70 px-3 py-2">
                          <p className="text-xs font-semibold text-lovable-ink">{action.title}</p>
                          <p className="mt-1 text-xs text-lovable-ink-muted">{action.reason}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </>
            );
          })()}
        </div>
      )}
    </Drawer>
  );
}
