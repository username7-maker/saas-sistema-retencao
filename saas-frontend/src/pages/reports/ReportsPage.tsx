import { useEffect, useState } from "react";
import { Activity, BarChart3, Briefcase, CalendarDays, FileText, Send, ShieldAlert, Sparkles, Wallet } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import toast from "react-hot-toast";

import { reportService, type AsyncJobStatusResponse, type DashboardReportType } from "../../services/reportService";
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Dialog } from "../../components/ui2";

interface ReportCardConfig {
  type: DashboardReportType;
  title: string;
  description: string;
  icon: LucideIcon;
  cadence: string;
  audience: string;
  highlights: string[];
}

const REPORT_CARDS: ReportCardConfig[] = [
  {
    type: "executive",
    title: "Executivo",
    description: "Visao geral de KPIs, distribuicao de risco, MRR e pulso da base.",
    icon: BarChart3,
    cadence: "Semanal",
    audience: "Owner e gestao",
    highlights: ["KPIs centrais", "MRR e churn", "Leitura de risco"],
  },
  {
    type: "retention",
    title: "Retencao",
    description: "Fila critica, MRR em risco, NPS e distribuicao de churn.",
    icon: ShieldAlert,
    cadence: "Diario",
    audience: "Operacao e lideranca",
    highlights: ["Fila vermelha", "MRR em risco", "Curva de NPS"],
  },
  {
    type: "commercial",
    title: "Comercial",
    description: "Pipeline, conversao por origem e leads sem resposta recente.",
    icon: Briefcase,
    cadence: "Semanal",
    audience: "Comercial",
    highlights: ["Pipeline", "CAC", "Leads parados"],
  },
  {
    type: "financial",
    title: "Financeiro",
    description: "Receita, inadimplencia, projeções e leitura executiva compacta.",
    icon: Wallet,
    cadence: "Mensal",
    audience: "Owner e financeiro",
    highlights: ["Receita recente", "Inadimplencia", "Projecoes"],
  },
  {
    type: "operational",
    title: "Operacional",
    description: "Check-ins, inatividade, janelas de pico e aniversariantes do dia.",
    icon: Activity,
    cadence: "Diario",
    audience: "Operacao",
    highlights: ["Top inativos", "Janelas de pico", "Relacionamento do dia"],
  },
  {
    type: "consolidated",
    title: "Consolidado",
    description: "Board pack mensal reunindo gestao, risco, receita e comercial.",
    icon: FileText,
    cadence: "Mensal",
    audience: "Lideranca",
    highlights: ["Board pack", "Resumo executivo", "Acoes recomendadas"],
  },
];

function initialLoadingMap(): Record<DashboardReportType, boolean> {
  return {
    executive: false,
    operational: false,
    commercial: false,
    financial: false,
    retention: false,
    consolidated: false,
  };
}

function reportCardTitle(type: DashboardReportType): string {
  return REPORT_CARDS.find((card) => card.type === type)?.title ?? type;
}

function buildQueuedStatus(jobId: string, jobType: string, status: string): AsyncJobStatusResponse {
  return {
    job_id: jobId,
    job_type: jobType,
    status,
    attempt_count: 0,
    max_attempts: 0,
    next_retry_at: null,
    started_at: null,
    completed_at: null,
    error_code: null,
    error_message: null,
    result: null,
    related_entity_type: null,
    related_entity_id: null,
  };
}

function dispatchStatusTone(status?: string | null): string {
  switch (status) {
    case "completed":
      return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
    case "failed":
      return "bg-rose-500/15 text-rose-300 border-rose-500/30";
    case "processing":
      return "bg-amber-500/15 text-amber-200 border-amber-500/30";
    default:
      return "bg-white/5 text-lovable-ink-muted border-white/10";
  }
}

function dispatchStatusLabel(status?: string | null): string {
  switch (status) {
    case "completed":
      return "Concluido";
    case "failed":
      return "Falhou";
    case "processing":
      return "Processando";
    case "pending":
      return "Na fila";
    default:
      return "Nao iniciado";
  }
}

export default function ReportsPage() {
  const [loadingByType, setLoadingByType] = useState<Record<DashboardReportType, boolean>>(initialLoadingMap);
  const [dispatching, setDispatching] = useState(false);
  const [confirmDispatch, setConfirmDispatch] = useState(false);
  const [dispatchStatus, setDispatchStatus] = useState<AsyncJobStatusResponse | null>(null);

  const handleDownload = async (type: DashboardReportType) => {
    setLoadingByType((prev) => ({ ...prev, [type]: true }));
    try {
      await reportService.exportDashboardPdf(type);
      toast.success(`Relatorio ${reportCardTitle(type)} baixado com sucesso.`);
    } catch {
      toast.error("Falha ao exportar PDF. Verifique se os dados desse dashboard estao disponiveis.");
    } finally {
      setLoadingByType((prev) => ({ ...prev, [type]: false }));
    }
  };

  const handleDispatchMonthly = async () => {
    setDispatching(true);
    try {
      const result = await reportService.dispatchMonthlyReports();
      setDispatchStatus(buildQueuedStatus(result.job_id, result.job_type, result.status));
      toast.success(result.message);
    } catch {
      toast.error("Falha ao disparar relatorio mensal.");
    } finally {
      setDispatching(false);
    }
  };

  useEffect(() => {
    if (!dispatchStatus || dispatchStatus.status === "completed" || dispatchStatus.status === "failed") {
      return undefined;
    }

    const timer = window.setTimeout(async () => {
      try {
        const nextStatus = await reportService.getMonthlyDispatchStatus(dispatchStatus.job_id);
        setDispatchStatus(nextStatus);
        if (nextStatus.status === "completed") {
          const sent = Number(nextStatus.result?.sent ?? 0);
          const failed = Number(nextStatus.result?.failed ?? 0);
          toast.success(`Disparo mensal concluido: ${sent} enviados, ${failed} falhas.`);
        } else if (nextStatus.status === "failed") {
          toast.error(nextStatus.error_message ?? "Falha ao processar disparo mensal.");
        }
      } catch {
        toast.error("Falha ao acompanhar o status do disparo mensal.");
      }
    }, 5000);

    return () => window.clearTimeout(timer);
  }, [dispatchStatus]);

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="font-heading text-2xl font-bold text-lovable-ink sm:text-3xl">Relatorios</h2>
          <p className="max-w-3xl text-sm text-lovable-ink-muted">
            Central premium para board packs de gestao e laudos de avaliacao. Aqui o time baixa materiais prontos para decisao,
            compartilhamento e acompanhamento mensal da academia.
          </p>
        </div>
        <Button variant="primary" onClick={() => setConfirmDispatch(true)} disabled={dispatching} className="w-full md:w-auto">
          <Send size={14} />
          {dispatching ? "Enfileirando..." : "Disparar relatorio mensal"}
        </Button>
      </header>

      <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        <Card className="border-white/10 bg-white/[0.03]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Sparkles size={18} className="text-lovable-primary" />
              Board packs de gestao
            </CardTitle>
            <CardDescription>
              PDFs premium desenhados para leitura rapida, reunindo indicadores, comparativos, narrativas curtas e acoes recomendadas.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {REPORT_CARDS.map((card) => {
              const Icon = card.icon;
              const isLoading = loadingByType[card.type];

              return (
                <article key={card.type} className="rounded-3xl border border-white/10 bg-[#121827] p-4">
                  <div className="mb-4 flex items-start justify-between gap-3">
                    <div>
                      <div className="mb-2 flex flex-wrap gap-2">
                        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">
                          {card.cadence}
                        </span>
                        <span className="rounded-full border border-lovable-primary/25 bg-lovable-primary/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-lovable-primary-light">
                          {card.audience}
                        </span>
                      </div>
                      <h3 className="flex items-center gap-2 text-base font-semibold text-lovable-ink">
                        <Icon size={18} className="text-lovable-primary" />
                        {card.title}
                      </h3>
                    </div>
                  </div>
                  <p className="mb-4 text-sm text-lovable-ink-muted">{card.description}</p>
                  <div className="mb-4 flex flex-wrap gap-2">
                    {card.highlights.map((highlight) => (
                      <span
                        key={highlight}
                        className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-lovable-ink-muted"
                      >
                        {highlight}
                      </span>
                    ))}
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="w-full"
                    onClick={() => void handleDownload(card.type)}
                    disabled={isLoading}
                  >
                    {isLoading ? "Gerando..." : "Baixar PDF premium"}
                  </Button>
                </article>
              );
            })}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="border-white/10 bg-white/[0.03]">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <CalendarDays size={18} className="text-lovable-primary" />
                Distribuicao mensal
              </CardTitle>
              <CardDescription>
                O consolidado mensal envia o board pack da lideranca por e-mail sem depender de geracao manual.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-[#121827] px-4 py-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-lovable-ink-muted">Ultimo disparo</p>
                  <p className="mt-1 text-sm font-semibold text-lovable-ink">{dispatchStatusLabel(dispatchStatus?.status)}</p>
                </div>
                <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${dispatchStatusTone(dispatchStatus?.status)}`}>
                  {dispatchStatus?.status ?? "idle"}
                </span>
              </div>
              <p className="text-sm text-lovable-ink-muted">
                O consolidado premium e o material indicado para owner, gerencia e reunioes mensais de resultado.
              </p>
              {dispatchStatus ? (
                <div className="rounded-2xl border border-white/10 bg-[#121827] p-4 text-sm">
                  <p className="text-lovable-ink-muted">
                    Tentativas: <span className="font-semibold text-lovable-ink">{dispatchStatus.attempt_count}</span>
                  </p>
                  {dispatchStatus.result ? (
                    <p className="mt-2 text-lovable-ink-muted">
                      Enviados: <span className="font-semibold text-lovable-ink">{String(dispatchStatus.result.sent ?? 0)}</span> · Falhas:{" "}
                      <span className="font-semibold text-lovable-ink">{String(dispatchStatus.result.failed ?? 0)}</span>
                    </p>
                  ) : null}
                  {dispatchStatus.error_message ? <p className="mt-2 text-lovable-danger">{dispatchStatus.error_message}</p> : null}
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-white/[0.03]">
            <CardHeader>
              <CardTitle className="text-lg">Laudos de avaliacao</CardTitle>
              <CardDescription>
                Os laudos premium de bioimpedancia agora existem em dois formatos dentro do perfil do aluno.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-lovable-ink-muted">
              <div className="rounded-2xl border border-white/10 bg-[#121827] p-4">
                <p className="font-semibold text-lovable-ink">Resumo do aluno</p>
                <p className="mt-1">Versao mais enxuta, com leitura corporal, comparativo e proximos passos.</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-[#121827] p-4">
                <p className="font-semibold text-lovable-ink">Relatorio tecnico</p>
                <p className="mt-1">Versao para coach com painel tecnico, comparativo e direcao de acompanhamento.</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Como usar esta central</CardTitle>
          <CardDescription>
            Use os relatorios individuais para leitura tática do dia a dia e o consolidado para a narrativa mensal da lideranca. Os laudos de
            avaliacao ficam no contexto do aluno, para nao misturar material clinico/técnico com board packs de gestao.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-[#121827] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-lovable-ink-muted">1. Analise</p>
            <p className="mt-2 text-sm text-lovable-ink-muted">Baixe o relatório certo para a frente certa: executivo, retenção, comercial, financeiro ou operacional.</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-[#121827] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-lovable-ink-muted">2. Compartilhe</p>
            <p className="mt-2 text-sm text-lovable-ink-muted">Use o consolidado como board pack mensal e os laudos de avaliação dentro do contexto do aluno.</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-[#121827] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-lovable-ink-muted">3. Execute</p>
            <p className="mt-2 text-sm text-lovable-ink-muted">Converta os alertas e ações recomendadas dos PDFs em tarefas, follow-ups e revisão de metas.</p>
          </div>
        </CardContent>
      </Card>

      <Dialog
        open={confirmDispatch}
        onClose={() => setConfirmDispatch(false)}
        title="Disparar relatorio mensal"
        description="O relatorio consolidado sera gerado e enviado por e-mail para os usuarios de lideranca. Deseja continuar?"
      >
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setConfirmDispatch(false)}>
            Cancelar
          </Button>
          <Button
            variant="primary"
            disabled={dispatching}
            onClick={() => {
              setConfirmDispatch(false);
              void handleDispatchMonthly();
            }}
          >
            {dispatching ? "Enfileirando..." : "Confirmar envio"}
          </Button>
        </div>
      </Dialog>
    </section>
  );
}
