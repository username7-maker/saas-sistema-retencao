import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Download, Printer } from "lucide-react";
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
import { Button, Card, CardContent } from "../../components/ui2";
import { bodyCompositionService } from "../../services/bodyCompositionService";
import type { BodyCompositionBodyFatContext, BodyCompositionMeasurementRow, BodyCompositionSex } from "../../types";

const PERIOD_OPTIONS = [
  { key: "30", label: "30 dias", days: 30 },
  { key: "90", label: "90 dias", days: 90 },
  { key: "180", label: "180 dias", days: 180 },
  { key: "all", label: "Todo historico", days: null },
] as const;

function formatPercent(value: number | null | undefined): string {
  return value == null ? "-" : `${value}%`;
}

function formatPp(value: number | null | undefined): string {
  return value == null ? "-" : `${value} p.p.`;
}

function sourceLabel(source: string | null | undefined): string {
  if (source === "anthropometry") return "Medidas manuais";
  if (source === "manual_override") return "Override manual";
  if (source === "bioimpedance") return "Bioimpedancia bruta";
  return "Fonte pendente";
}

function methodLabel(method: string | null | undefined): string {
  if (method === "geneos_composite") return "Navy + RFM";
  if (method === "navy_circumference") return "Navy por circunferencias";
  if (method === "rfm") return "RFM";
  if (method === "manual_override") return "Override manual";
  if (method === "legacy_bioimpedance") return "Bioimpedancia bruta";
  return "Metodo pendente";
}

function confidenceLabel(confidence: string | null | undefined): string {
  if (confidence === "high") return "Alta";
  if (confidence === "medium_high") return "Media-alta";
  if (confidence === "medium") return "Media";
  if (confidence === "low") return "Baixa";
  if (confidence === "inconsistent") return "Inconsistente";
  return "Nao calculada";
}

function BodyCompositionReportPage() {
  const { memberId, evaluationId } = useParams<{ memberId: string; evaluationId: string }>();
  const [periodKey, setPeriodKey] = useState<(typeof PERIOD_OPTIONS)[number]["key"]>("all");
  const [historyNow] = useState(() => Date.now());

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
    const threshold = historyNow - selectedPeriod.days * 24 * 60 * 60 * 1000;
    return report.history_series.map((series) => ({
      ...series,
      points: series.points.filter((point) => new Date(point.measured_at).getTime() >= threshold),
    }));
  }, [historyNow, reportQuery.data, selectedPeriod.days]);

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
  const obesityMetrics = report.risk_metrics.filter((metric) => ["bmi", "body_fat_used_percent", "visceral_fat_level"].includes(metric.key));
  const additionalMetrics = [
    metricIndex.get("fat_free_mass_kg"),
    metricIndex.get("body_water_kg"),
    metricIndex.get("body_water_percent"),
    metricIndex.get("skeletal_muscle_kg"),
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
          <Button size="sm" variant="primary" onClick={() => void handleOpenPdf("summary")}>
            <Download size={14} />
            Abrir PDF
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

          <div className="mt-4 space-y-6">
            <MetricHighlights metrics={report.primary_cards} />
            <BodyFatContextPanel context={report.body_fat_context ?? null} />

            <div className="grid gap-8 xl:grid-cols-[1.9fr_0.95fr]">
              <div className="space-y-8">
                <CompositionAnalysisTable metrics={report.composition_metrics} />
                {(report.measurement_rows ?? []).some((row) => row.current_value != null || row.previous_value != null) ? (
                  <section className="rounded-none border border-[#d8d2ca] bg-[#fbfaf7]">
                    <div className="border-b border-[#d8d2ca] px-4 py-3">
                      <h2 className="text-lg font-semibold text-[#15110f]">Medidas corporais</h2>
                      <p className="text-xs text-[#665f57]">Perimetria usada para acompanhar evolucao. Apenas pescoco, cintura/abdomen e quadril entram no calculo quando aplicavel.</p>
                    </div>
                    <div className="grid gap-4 p-4 xl:grid-cols-[1.1fr_0.9fr]">
                      <BodyMeasurementMap rows={report.measurement_rows ?? []} sex={report.header.sex} />
                      <div className="overflow-x-auto border border-[#e8e3dc]">
                        <table className="w-full text-sm">
                          <thead className="bg-[#f0eee9] text-xs uppercase tracking-[0.18em] text-[#6d6258]">
                            <tr>
                              <th className="px-4 py-3 text-left">Medida</th>
                              <th className="px-4 py-3 text-right">Atual</th>
                              <th className="px-4 py-3 text-right">Anterior</th>
                              <th className="px-4 py-3 text-right">Variacao</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(report.measurement_rows ?? [])
                              .filter((row) => row.current_value != null || row.previous_value != null)
                              .map((row) => (
                                <tr key={row.key} className="border-t border-[#e8e3dc]">
                                  <td className="px-4 py-3 font-medium text-[#15110f]">{row.label}</td>
                                  <td className="px-4 py-3 text-right">{row.formatted_current}</td>
                                  <td className="px-4 py-3 text-right">{row.formatted_previous}</td>
                                  <td className="px-4 py-3 text-right">{row.formatted_delta}</td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </section>
                ) : null}
                <BandAnalysisPanel
                  title="Analise Musculo-Gordura"
                  subtitle="Leitura visual do quanto o peso total esta associado a massa muscular e gordura corporal."
                  metrics={report.muscle_fat_metrics}
                />
                <BandAnalysisPanel
                  title="Analise de Obesidade"
                  subtitle="Indicadores de acompanhamento, sem interpretacao diagnostica."
                  metrics={report.risk_metrics.filter((metric) => ["bmi", "body_fat_used_percent", "visceral_fat_level", "waist_hip_ratio"].includes(metric.key))}
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
                    aria-pressed={periodKey === option.key}
                    className={
                      periodKey === option.key
                        ? "border-[#1d536f] bg-[#6fa7c7] text-[#061019] shadow-none hover:bg-[#7db6d4]"
                        : "border-[#1d536f]/80 bg-[#fbfaf7] text-[#1d536f] shadow-none hover:bg-[#edf6fa]"
                    }
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

function BodyMeasurementMap({ rows, sex }: { rows: BodyCompositionMeasurementRow[]; sex: BodyCompositionSex | null }) {
  const rowMap = new Map(rows.map((row) => [row.key, row]));
  const mapAsset = sex === "female" ? "/body-maps/body-map-front-female.png" : "/body-maps/body-map-front-male.png";
  const mapAlt = sex === "female" ? "Mapa corporal frontal feminino de medidas" : "Mapa corporal frontal masculino de medidas";
  const points: Array<{ key: string; side: "left" | "right"; tone: string }> = [
    { key: "shoulders_cm", side: "left", tone: "#5ca6b3" },
    { key: "neck_cm", side: "right", tone: "#6fa7c7" },
    { key: "right_arm_relaxed_cm", side: "left", tone: "#86aa62" },
    { key: "chest_cm", side: "right", tone: "#6d7fab" },
    { key: "right_arm_flexed_cm", side: "left", tone: "#6f9d52" },
    { key: "left_arm_relaxed_cm", side: "right", tone: "#86aa62" },
    { key: "waist_cm", side: "left", tone: "#7fb8bc" },
    { key: "left_arm_flexed_cm", side: "right", tone: "#6f9d52" },
    { key: "hip_cm", side: "left", tone: "#8d69a6" },
    { key: "abdomen_cm", side: "right", tone: "#8c8a84" },
    { key: "right_thigh_cm", side: "left", tone: "#d99b42" },
    { key: "left_thigh_cm", side: "right", tone: "#d99b42" },
    { key: "right_calf_cm", side: "left", tone: "#c86b61" },
    { key: "left_calf_cm", side: "right", tone: "#c86b61" },
  ];
  const visiblePoints = points
    .map((point) => ({ ...point, row: rowMap.get(point.key) }))
    .filter((point): point is typeof point & { row: BodyCompositionMeasurementRow } => Boolean(point.row && (point.row.current_value != null || point.row.previous_value != null)));
  const leftPoints = visiblePoints.filter((point) => point.side === "left");
  const rightPoints = visiblePoints.filter((point) => point.side === "right");
  const hasVisibleRows = visiblePoints.length > 0;

  return (
    <div className="border border-[#e8e3dc] bg-[#f7f4ef] p-4">
      <div>
        <p className="text-xs uppercase tracking-[0.18em] text-[#6d6258]">Mapa corporal de medidas</p>
        <p className="mt-1 text-xs text-[#665f57]">Boneco anatomico generico para localizar perimetria. Nao usa foto do aluno.</p>
      </div>
      <div className="mt-4 overflow-hidden border border-[#e0d9cf] bg-white px-4 py-5">
        <div className="grid min-h-[660px] grid-cols-[minmax(132px,1fr)_minmax(230px,300px)_minmax(132px,1fr)] items-center gap-4">
          <MeasurementBubbleColumn points={leftPoints} side="left" />
          <div className="relative flex min-h-[610px] items-center justify-center">
            <img src={mapAsset} alt={mapAlt} className="h-[610px] w-full object-contain" loading="lazy" />
          </div>
          <MeasurementBubbleColumn points={rightPoints} side="right" />
        </div>
        <div className="mx-auto mt-4 max-w-[86%] border border-[#e3ddd4] bg-[#fcfbf7]/95 px-3 py-2 text-xs text-[#665f57]">
          <span className="font-semibold text-[#332d28]">Leitura:</span> baloes mostram a medida atual quando existe; se a avaliacao atual nao tem perimetria, mostram a ultima medida anterior.
        </div>
        {!hasVisibleRows ? (
          <p className="mx-auto mt-3 max-w-[220px] border border-[#e3ddd4] bg-[#fcfbf7] p-3 text-xs text-[#665f57]">Sem medidas atuais para marcar no mapa.</p>
        ) : null}
      </div>
    </div>
  );
}

function MeasurementBubbleColumn({
  points,
  side,
}: {
  points: Array<{ key: string; side: "left" | "right"; tone: string; row: BodyCompositionMeasurementRow }>;
  side: "left" | "right";
}) {
  return (
    <div className="flex h-full flex-col justify-center gap-2.5">
      {points.map((point) => (
        <MeasurementBubble key={point.key} row={point.row} side={side} tone={point.tone} />
      ))}
    </div>
  );
}

function MeasurementBubble({
  row,
  side,
  tone,
}: {
  row: BodyCompositionMeasurementRow;
  side: "left" | "right";
  tone: string;
}) {
  const hasCurrent = row.current_value != null;
  const value = hasCurrent ? row.formatted_current : row.formatted_previous;
  const caption = hasCurrent ? "Atual" : "Anterior";
  const sideClass = side === "left" ? "text-left" : "text-right";
  const accentSideClass = side === "left" ? "left-0" : "right-0";

  return (
    <div className={`relative min-h-[66px] border border-[#d8d2ca] bg-[#fcfbf7]/95 px-3 py-2 shadow-[0_8px_18px_rgba(21,17,15,0.06)] ${sideClass}`}>
      <span className={`absolute top-0 h-full w-1 ${accentSideClass}`} style={{ backgroundColor: tone }} />
      <span className={`absolute top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full ${accentSideClass}`} style={{ backgroundColor: tone }} />
      <div className={side === "left" ? "pl-2" : "pr-2"}>
        <p className="text-[0.62rem] uppercase tracking-[0.16em] text-[#786f66]">{caption}</p>
        <p className="mt-0.5 text-[11px] font-semibold leading-tight text-[#332d28]">{row.label}</p>
        <p className="text-sm font-bold text-[#15110f]">{value}</p>
      </div>
    </div>
  );
}

function BodyFatContextPanel({ context }: { context: BodyCompositionBodyFatContext | null }) {
  if (!context) return null;
  return (
    <section className="rounded-none border border-[#d8d2ca] bg-[#fbfaf7]">
      <div className="border-b border-[#d8d2ca] px-4 py-3">
        <p className="text-xs uppercase tracking-[0.18em] text-[#6d6258]">Fonte oficial da gordura corporal</p>
        <h2 className="mt-1 text-xl font-semibold text-[#15110f]">{formatPercent(context.used_percent)}</h2>
        <p className="mt-1 text-xs text-[#665f57]">
          Percentual tratado como estimativa operacional, sem valor diagnostico clinico.
        </p>
      </div>
      <div className="grid gap-px bg-[#e8e3dc] md:grid-cols-4">
        <ContextMetric label="Fonte usada no relatorio" value={sourceLabel(context.used_source)} />
        <ContextMetric label="Metodo" value={methodLabel(context.method)} />
        <ContextMetric label="Confianca" value={confidenceLabel(context.confidence)} />
        <ContextMetric
          label="Faixa estimada"
          value={context.range_min != null || context.range_max != null ? `${formatPercent(context.range_min)} - ${formatPercent(context.range_max)}` : "-"}
        />
        <ContextMetric label="Bioimpedancia bruta" value={formatPercent(context.bioimpedance_raw_percent)} />
        <ContextMetric label="Antropometria" value={formatPercent(context.anthropometric_percent)} />
        <ContextMetric label="Diferenca entre fontes" value={formatPp(context.difference_between_sources)} />
        <ContextMetric label="Revisao manual" value={context.manual_review_required ? (context.manual_review_completed ? "Concluida" : "Obrigatoria") : "Nao exigida"} />
      </div>
      {context.quality_flags.length > 0 ? (
        <div className="flex flex-wrap gap-2 border-t border-[#d8d2ca] px-4 py-3 text-xs text-[#665f57]">
          {context.quality_flags.map((flag) => (
            <span key={flag} className="rounded-full border border-[#d8d2ca] bg-[#f0eee9] px-2.5 py-1">
              {flag}
            </span>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function ContextMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-[#fcfbf7] px-4 py-3">
      <p className="text-[0.65rem] uppercase tracking-[0.16em] text-[#786f66]">{label}</p>
      <p className="mt-1 text-sm font-semibold text-[#15110f]">{value}</p>
    </div>
  );
}
