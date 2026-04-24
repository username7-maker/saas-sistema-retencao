import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Download, MessageCircle, Printer } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import toast from "react-hot-toast";

import {
  BandAnalysisPanel,
  ComparisonTable,
  CompositionAnalysisTable,
  EmptyStateSegmentalAnalysis,
  InsightPanel,
  HistoryCompositionPanel,
  MetricHighlights,
  ReportHeaderCard,
  RightRailSummary,
} from "../../components/assessments/bodyCompositionReport/BodyCompositionReportBlocks";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle } from "../../components/ui2";
import { bodyCompositionService } from "../../services/bodyCompositionService";

const PERIOD_OPTIONS = [
  { key: "30", label: "30 dias", days: 30 },
  { key: "90", label: "90 dias", days: 90 },
  { key: "180", label: "180 dias", days: 180 },
  { key: "all", label: "Todo historico", days: null },
] as const;

export function BodyCompositionReportPage() {
  const { memberId, evaluationId } = useParams<{ memberId: string; evaluationId: string }>();
  const [periodKey, setPeriodKey] = useState<(typeof PERIOD_OPTIONS)[number]["key"]>("all");

  const reportQuery = useQuery({
    queryKey: ["body-composition-report", memberId, evaluationId],
    queryFn: () => bodyCompositionService.getReport(memberId ?? "", evaluationId ?? ""),
    enabled: Boolean(memberId && evaluationId),
    staleTime: 60 * 1000,
  });

  const selectedPeriod = PERIOD_OPTIONS.find((item) => item.key === periodKey) ?? PERIOD_OPTIONS[PERIOD_OPTIONS.length - 1];
  const filteredHistory = useMemo(() => {
    const report = reportQuery.data;
    if (!report) return [];
    if (selectedPeriod.days == null) return report.history_series;
    const threshold = Date.now() - selectedPeriod.days * 24 * 60 * 60 * 1000;
    return report.history_series.map((series) => ({
      ...series,
      points: series.points.filter((point) => new Date(point.measured_at).getTime() >= threshold),
    }));
  }, [reportQuery.data, selectedPeriod.days]);

  if (reportQuery.isLoading) {
    return <LoadingPanel text="Carregando relatorio premium..." />;
  }

  if (reportQuery.isError || !reportQuery.data) {
    return (
      <section className="space-y-4">
        <Link to={memberId ? `/assessments/members/${memberId}?tab=bioimpedancia` : "/assessments"} className="inline-flex items-center gap-2 text-sm text-lovable-ink-muted">
          <ArrowLeft size={14} />
          Voltar
        </Link>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-lovable-ink-muted">Nao foi possivel carregar o relatorio premium desta bioimpedancia.</p>
          </CardContent>
        </Card>
      </section>
    );
  }

  const report = reportQuery.data;
  const metricIndex = new Map(
    [...report.composition_metrics, ...report.risk_metrics, ...report.goal_metrics, ...report.muscle_fat_metrics].map((metric) => [metric.key, metric]),
  );
  const obesityMetrics = report.risk_metrics.filter((metric) => ["bmi", "body_fat_percent", "visceral_fat_level"].includes(metric.key));
  const additionalMetrics = [
    metricIndex.get("fat_free_mass_kg"),
    metricIndex.get("body_water_kg"),
    metricIndex.get("protein_kg"),
    metricIndex.get("inorganic_salt_kg"),
    metricIndex.get("physical_age"),
  ].filter((metric): metric is NonNullable<typeof metric> => Boolean(metric));

  async function handleOpenPdf(kind: "summary" | "technical") {
    if (!memberId || !evaluationId) return;
    const popup = window.open("", "_blank");
    try {
      if (popup) popup.opener = null;
      await bodyCompositionService.openPdf(memberId, evaluationId, kind, popup);
    } catch {
      popup?.close();
      toast.error(kind === "technical" ? "Nao foi possivel abrir o relatorio tecnico." : "Nao foi possivel abrir o resumo do aluno.");
    }
  }

  return (
    <section className="space-y-6 print:space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between print:hidden">
        <Link to={`/assessments/members/${memberId}?tab=bioimpedancia`} className="inline-flex items-center gap-2 text-sm font-medium text-lovable-ink-muted transition hover:text-lovable-ink">
          <ArrowLeft size={14} />
          Voltar para bioimpedancia
        </Link>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" onClick={() => void handleOpenPdf("summary")}>
            <Download size={14} />
            Resumo do aluno
          </Button>
          <Button size="sm" variant="secondary" onClick={() => void handleOpenPdf("technical")}>
            <Download size={14} />
            Relatorio tecnico
          </Button>
          <Button size="sm" variant="secondary" onClick={() => window.print()}>
            <Printer size={14} />
            Imprimir
          </Button>
        </div>
      </div>

      <article className="overflow-hidden rounded-[30px] border border-[#d2ccc4] bg-[#fcfbf7] text-[#15110f] shadow-[0_24px_60px_rgba(0,0,0,0.18)] print:rounded-none print:border-none print:bg-white print:shadow-none">
        <div className="p-6 md:p-8 print:p-0">
          <ReportHeaderCard
            header={report.header}
            dataQualityFlags={report.data_quality_flags}
            parsingConfidence={report.parsing_confidence}
          />

          <div className="mt-5 print:hidden">
            <Card className="border-[#d8d5d0] bg-[#fffdf9] shadow-none">
              <CardHeader>
                <CardTitle className="text-[#171311]">Relatorio premium pronto</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-sm text-[#5f5650]">
                    Este laudo ja esta pronto para acompanhamento, compartilhamento com o aluno e exportacao.
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {report.data_quality_flags.map((flag) => (
                      <Badge key={flag} variant="neutral" className="border-[#d8d5d0] bg-[#f7f5f1] text-[#554c45]">
                        {flag}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="primary" onClick={() => void handleOpenPdf("summary")}>
                    <Download size={14} />
                    Abrir PDF
                  </Button>
                  <Link to={`/assessments/members/${memberId}?tab=bioimpedancia`}>
                    <Button size="sm" variant="secondary">
                      <MessageCircle size={14} />
                      Voltar ao workspace
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="mt-6 space-y-6">
            <MetricHighlights metrics={report.primary_cards} />

            <div className="grid gap-8 xl:grid-cols-[1.9fr_0.95fr]">
              <div className="space-y-8">
                <CompositionAnalysisTable metrics={report.composition_metrics} />
                <BandAnalysisPanel
                  title="Analise Musculo-Gordura"
                  subtitle="Leitura visual do quanto o peso total esta associado a massa muscular e gordura corporal."
                  metrics={report.muscle_fat_metrics}
                />
                <BandAnalysisPanel
                  title="Analise de Obesidade"
                  subtitle="Indicadores de acompanhamento, sem interpretacao diagnostica."
                  metrics={report.risk_metrics.filter((metric) => ["bmi", "body_fat_percent", "visceral_fat_level", "waist_hip_ratio"].includes(metric.key))}
                />
              </div>

              <RightRailSummary
                scoreMetric={metricIndex.get("health_score") ?? report.primary_cards.find((metric) => metric.key === "health_score") ?? null}
                goalMetrics={report.goal_metrics}
                obesityMetrics={obesityMetrics}
                additionalMetrics={additionalMetrics}
                waistHipMetric={metricIndex.get("waist_hip_ratio") ?? null}
                visceralMetric={metricIndex.get("visceral_fat_level") ?? null}
              />
            </div>

            <section className="space-y-4">
              <div className="flex flex-wrap gap-2 print:hidden">
                {PERIOD_OPTIONS.map((option) => (
                  <Button
                    key={option.key}
                    size="sm"
                    variant={periodKey === option.key ? "primary" : "secondary"}
                    onClick={() => setPeriodKey(option.key)}
                  >
                    {option.label}
                  </Button>
                ))}
              </div>
              <HistoryCompositionPanel series={filteredHistory} />
              <ComparisonTable rows={report.comparison_rows} />
              <InsightPanel
                insights={report.insights}
                teacherNotes={report.teacher_notes}
                methodologicalNote={report.methodological_note}
              />
              {!report.segmental_analysis_available ? <EmptyStateSegmentalAnalysis /> : null}
            </section>
          </div>
        </div>
      </article>
    </section>
  );
}

export default BodyCompositionReportPage;
