import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Download, Printer, Share2 } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import toast from "react-hot-toast";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { ErrorBoundary } from "../../components/common/ErrorBoundary";
import { Button, Card, CardContent } from "../../components/ui2";
import { bodyCompositionService } from "../../services/bodyCompositionService";
import { assessmentService } from "../../services/assessmentService";
import type {
  BodyCompositionBodyFatContext,
  BodyCompositionInsight,
  BodyCompositionMeasurementRow,
  BodyCompositionMetricCard,
  BodyCompositionReferenceMetric,
  BodyCompositionReport,
  BodyCompositionReportHeader,
  BodyCompositionReportMetric,
  BodyCompositionSex,
  CalculationOrigin,
} from "../../types";
import { calculationOriginLabel } from "../../utils/calculationOrigins";

const CORDEX_LOGO_SRC = "/brand/cordex-logo-report.png";
const PROGYM_LOGO_SRC = "/progym-logo.png";
const EMPTY_VALUES = new Set(["", "-", "--"]);
const MOBILE_REPORT_READING_ENABLED = import.meta.env.VITE_MOBILE_REPORT_READING_V1 === "true";

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  } catch {
    return String(value);
  }
}

function formatNumber(value: number | null | undefined, unit?: string | null): string {
  if (value == null || !Number.isFinite(value)) return "-";
  const abs = Math.abs(value);
  const minimumDigits = Number.isInteger(value) ? 0 : 1;
  const maximumDigits = abs >= 100 && Number.isInteger(value) ? 0 : 1;
  const formatted = value.toLocaleString("pt-BR", {
    minimumFractionDigits: minimumDigits,
    maximumFractionDigits: maximumDigits,
  });
  return unit ? `${formatted} ${unit}` : formatted;
}

function formatPercent(value: number | null | undefined): string {
  return value == null || !Number.isFinite(value) ? "-" : `${value.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

function headerValue(value: number | null | undefined, unit: string): string {
  return value == null ? "-" : `${formatNumber(value)} ${unit}`;
}

function sexLabel(sex: BodyCompositionSex | null | undefined): string {
  if (sex === "male") return "Masculino";
  if (sex === "female") return "Feminino";
  return "Nao informado";
}

function isPresentMetric(metric: BodyCompositionMetricCard | BodyCompositionReferenceMetric | null | undefined): boolean {
  return Boolean(metric && !EMPTY_VALUES.has(String(metric.formatted_value ?? "").trim()));
}

function metricByKey<T extends { key: string }>(metrics: T[], ...keys: string[]): T | null {
  for (const key of keys) {
    const match = metrics.find((metric) => metric && metric.key === key);
    if (match) return match;
  }
  return null;
}

function metricValue(metric: BodyCompositionMetricCard | BodyCompositionReferenceMetric | null | undefined): string {
  return isPresentMetric(metric) ? String(metric?.formatted_value) : "-";
}

function sourceLabel(source: string | null | undefined): string {
  if (source === "bioimpedance") return "Bioimpedancia";
  if (source === "anthropometry" || source === "manual_anthropometry") return "Dobras e medidas";
  if (source === "manual_override") return "Informado manualmente";
  if (source === "geneos_composite") return "Metodo composto GeneOS";
  return "Fonte pendente";
}

function methodLabel(method: string | null | undefined): string {
  if (method === "legacy_bioimpedance" || method === "bioimpedance") return "Leitura da bioimpedancia";
  if (method === "geneos_composite") return "Metodo composto";
  if (method === "navy_circumference") return "Circunferencias";
  if (method === "skinfold_protocol") return "Protocolo de dobras";
  if (method === "rfm") return "RFM";
  if (method === "manual_override") return "Informado manualmente";
  return "Metodo pendente";
}

function statusLabel(status: string | null | undefined): string {
  if (status === "low") return "Abaixo";
  if (status === "adequate") return "Normal";
  if (status === "monitor") return "Monitorar";
  if (status === "high") return "Acima";
  return "Sem faixa";
}

function statusClass(status: string | null | undefined): string {
  if (status === "low") return "text-[#b45309]";
  if (status === "monitor") return "text-[#a16207]";
  if (status === "high") return "text-[#b91c1c]";
  if (status === "adequate") return "text-[#047857]";
  return "text-[#7a7168]";
}

function metricReference(metric: BodyCompositionReferenceMetric): string {
  if (metric.reference_min == null && metric.reference_max == null) {
    if (metric.key === "body_fat_used_percent" && metric.status === "unknown") {
      return "Sem faixa clínica validada";
    }
    return "Sem faixa";
  }
  if (metric.reference_min != null && metric.reference_max != null) {
    return `${formatNumber(metric.reference_min)} - ${formatNumber(metric.reference_max)}${metric.unit ? ` ${metric.unit}` : ""}`;
  }
  if (metric.reference_min != null) return `>= ${formatNumber(metric.reference_min)}${metric.unit ? ` ${metric.unit}` : ""}`;
  return `<= ${formatNumber(metric.reference_max)}${metric.unit ? ` ${metric.unit}` : ""}`;
}

interface ReportCalculationOrigins {
  basal_metabolic_rate_origin?: CalculationOrigin | null;
  muscle_mass_origin?: CalculationOrigin | null;
}

function metricOriginLabel(
  metric: BodyCompositionMetricCard | BodyCompositionReferenceMetric | null | undefined,
  fallbackOrigin?: CalculationOrigin | null,
): string {
  const suppliedLabel = metric?.origin_label?.trim();
  return suppliedLabel || calculationOriginLabel(fallbackOrigin);
}

function metricStatusLabel(metric: BodyCompositionReferenceMetric): string {
  if (metric.status === "unknown" && metric.position_label?.trim()) return metric.position_label;
  return statusLabel(metric.status);
}

function metricExplanation(
  metric: BodyCompositionReferenceMetric,
  context?: BodyCompositionBodyFatContext | null,
  origins?: ReportCalculationOrigins,
): string {
  const key = metric.key;
  if (key === "body_fat_used_percent") {
    if (context?.used_source === "bioimpedance") return "Leitura de gordura informada pela bioimpedancia";
    if (context?.used_source === "manual_override") return "Percentual informado pelo profissional";
    return "Estimativa por protocolo de dobras e medidas";
  }
  if (key === "muscle_mass_kg") return metricOriginLabel(metric, origins?.muscle_mass_origin);
  if (key === "basal_metabolic_rate_kcal" || key === "bmr") {
    return metricOriginLabel(metric, origins?.basal_metabolic_rate_origin);
  }
  const labels: Record<string, string> = {
    bmi: "Indice entre peso e altura",
    visceral_fat_level: "Indice informado no exame",
    waist_hip_ratio: "Relacao calculada por medidas",
    body_water_kg: "Agua corporal informada no exame",
    body_water_percent: "Percentual de agua sobre o peso",
    protein_kg: "Proteina informada no exame",
    inorganic_salt_kg: "Minerais informados no exame",
    skeletal_muscle_kg: "Musculo esqueletico informado",
    skeletal_muscle_percent: "Músculo esquelético informado pela bioimpedância",
    fat_mass_estimated_kg: "Massa de gordura calculada pelo percentual oficial",
    fat_free_mass_kg: "Massa livre de gordura informada",
    lean_mass_estimated_kg: "Massa livre estimada pelo percentual oficial",
    physical_age: "Idade fisica informada no exame",
  };
  return labels[key] ?? "Indicador de acompanhamento";
}

function bodyFatPanelDescription(source: string | null | undefined): string {
  if (source === "bioimpedance") return "Percentual lido da bioimpedancia porque esta avaliacao nao tem dobras/medidas suficientes.";
  if (source === "manual_override") return "Percentual informado manualmente pelo profissional responsavel.";
  return "Percentual estimado por dobras e medidas conforme o protocolo selecionado.";
}

function metricSource(
  metric: BodyCompositionReferenceMetric,
  context: BodyCompositionBodyFatContext | null,
  origins?: ReportCalculationOrigins,
): { group: "bioimpedance" | "measurements"; label: string } {
  const suppliedLabel = metric.origin_label?.trim();
  if (suppliedLabel) {
    return {
      group: suppliedLabel.toLocaleLowerCase("pt-BR").includes("bioimped") ? "bioimpedance" : "measurements",
      label: suppliedLabel,
    };
  }
  const usedSource = context?.used_source ?? null;
  if (["body_fat_used_percent", "fat_mass_estimated_kg", "lean_mass_estimated_kg"].includes(metric.key)) {
    if (usedSource === "bioimpedance") return { group: "bioimpedance", label: "Bioimpedancia" };
    if (usedSource === "manual_override") return { group: "measurements", label: "Manual" };
    return { group: "measurements", label: "Dobras e medidas" };
  }
  if (metric.key === "muscle_mass_kg") {
    return { group: "measurements", label: calculationOriginLabel(origins?.muscle_mass_origin) };
  }
  if (metric.key === "basal_metabolic_rate_kcal" || metric.key === "bmr") {
    return { group: "measurements", label: calculationOriginLabel(origins?.basal_metabolic_rate_origin) };
  }
  if (metric.key === "waist_hip_ratio") return { group: "measurements", label: "Medidas corporais" };
  return { group: "bioimpedance", label: "Bioimpedancia" };
}

function filterCompositionMetrics(metrics: BodyCompositionReferenceMetric[]): BodyCompositionReferenceMetric[] {
  const byKey = new Map(metrics.map((metric) => [metric.key, metric]));
  const hasEstimatedFatMass = isPresentMetric(byKey.get("fat_mass_estimated_kg"));
  const hasCanonicalFatFreeMass = isPresentMetric(byKey.get("fat_free_mass_kg"));
  return metrics.filter((metric) => {
    if (!isPresentMetric(metric)) return false;
    if (["body_fat_bioimpedance_percent", "body_fat_anthropometric_percent", "body_fat_kg"].includes(metric.key)) return false;
    if (metric.key === "body_fat_kg" && hasEstimatedFatMass) return false;
    if (metric.key === "lean_mass_estimated_kg" && hasCanonicalFatFreeMass) return false;
    return true;
  });
}

function bodyMapAsset(sex: BodyCompositionSex | null | undefined): string {
  return sex === "female" ? "/body-maps/body-map-front-female.png" : "/body-maps/body-map-front-male.png";
}

function BodyCompositionReportPage() {
  const { memberId, evaluationId, assessmentId } = useParams<{
    memberId: string;
    evaluationId?: string;
    assessmentId?: string;
  }>();
  const isAnthropometry = Boolean(assessmentId);
  const reportId = assessmentId ?? evaluationId;

  useEffect(() => {
    document.body.classList.add("body-composition-report-print");
    return () => document.body.classList.remove("body-composition-report-print");
  }, []);

  const reportQuery = useQuery({
    queryKey: [isAnthropometry ? "anthropometry-report" : "body-composition-report", memberId, reportId],
    queryFn: () => isAnthropometry
      ? assessmentService.getAnthropometryReport(memberId ?? "", reportId ?? "")
      : bodyCompositionService.getReport(memberId ?? "", reportId ?? ""),
    enabled: Boolean(memberId && reportId),
    staleTime: 60 * 1000,
  });

  if (reportQuery.isLoading) {
    return <LoadingPanel text="Carregando relatorio premium..." />;
  }

  if (reportQuery.isError || !reportQuery.data) {
    return (
      <section className="space-y-4">
        <Link to={memberId ? `/assessments/members/${memberId}?tab=${isAnthropometry ? "registro" : "bioimpedancia"}` : "/assessments"} className="inline-flex items-center gap-2 text-sm text-lovable-ink-muted">
          <ArrowLeft size={14} />
          Voltar
        </Link>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-lovable-ink-muted">Nao foi possivel carregar o relatorio premium desta avaliacao.</p>
          </CardContent>
        </Card>
      </section>
    );
  }

  const report = reportQuery.data;
  const isSemanticV2 = report.contract_version === "body-composition-report-v2"
    && Array.isArray(report.metrics)
    && report.score != null
    && report.goals != null;
  const reportHeader: BodyCompositionReportHeader = report.header && typeof report.header === "object"
    ? report.header
    : {
        member_name: "Aluno",
        gym_name: null,
        trainer_name: null,
        measured_at: "",
        age_years: null,
        sex: null,
        height_cm: null,
        weight_kg: null,
      };
  // Reports created by older releases can omit collection fields that are now
  // required by the API contract. Keep the presentation usable while those
  // historical records are progressively enriched.
  const primaryCards = Array.isArray(report.primary_cards) ? report.primary_cards : [];
  const compositionMetrics = Array.isArray(report.composition_metrics) ? report.composition_metrics : [];
  const muscleFatMetrics = Array.isArray(report.muscle_fat_metrics) ? report.muscle_fat_metrics : [];
  const riskMetrics = Array.isArray(report.risk_metrics) ? report.risk_metrics : [];
  const goalMetrics = Array.isArray(report.goal_metrics) ? report.goal_metrics : [];
  const measurementRows = Array.isArray(report.measurement_rows) ? report.measurement_rows : [];
  const insights = Array.isArray(report.insights) ? report.insights : [];
  const allReferenceMetrics = [...compositionMetrics, ...riskMetrics, ...goalMetrics, ...muscleFatMetrics];
  const scoreMetric = metricByKey([...riskMetrics, ...primaryCards], "health_score");
  const reportScore = report.score_total != null ? formatNumber(report.score_total) : metricValue(scoreMetric);
  const physicalAgeMetric = metricByKey(riskMetrics, "physical_age");
  const bmrMetric = metricByKey(primaryCards, "basal_metabolic_rate_kcal", "bmr");
  const muscleMassMetric = metricByKey(primaryCards, "muscle_mass_kg");
  const leadInsight = insights[0] ?? null;
  const keyIndicators = [
    metricByKey(allReferenceMetrics, "bmi"),
    metricByKey(allReferenceMetrics, "body_fat_used_percent"),
    metricByKey(allReferenceMetrics, "visceral_fat_level"),
    metricByKey(allReferenceMetrics, "waist_hip_ratio"),
  ].filter((metric): metric is BodyCompositionReferenceMetric => Boolean(metric && isPresentMetric(metric)));
  const detailMetrics = filterCompositionMetrics(compositionMetrics);
  const cleanGoalMetrics = goalMetrics.filter(isPresentMetric);

  async function handleOpenPdf(kind: "summary" | "technical") {
    if (!memberId || !reportId) return;
    const popup = window.open("", "_blank");
    try {
      if (isAnthropometry) {
        await assessmentService.openAnthropometryPdf(memberId, reportId, popup);
      } else {
        await bodyCompositionService.openPdf(memberId, reportId, kind, popup);
      }
    } catch {
      popup?.close();
      toast.error(kind === "technical" ? "Nao foi possivel abrir o relatorio tecnico." : "Nao foi possivel abrir o resumo do aluno.");
    }
  }

  async function handleShare() {
    try {
      const data = {
        title: `Relatorio de avaliacao - ${reportHeader.member_name}`,
        text: "Relatorio de avaliacao fisica Cordex",
        url: window.location.href,
      };
      if (navigator.share) await navigator.share(data);
      else {
        await navigator.clipboard.writeText(window.location.href);
        toast.success("Link do relatorio copiado.");
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      toast.error("Nao foi possivel compartilhar o relatorio.");
    }
  }

  return (
    <section className={`body-composition-report-page space-y-6 print:space-y-0${MOBILE_REPORT_READING_ENABLED ? " mobile-report-reading-v1" : ""}`}>
      <div className="sticky top-[env(safe-area-inset-top)] z-20 -mx-3 flex flex-col gap-3 border-b border-lovable-border bg-lovable-bg/95 px-3 py-2 backdrop-blur md:static md:mx-0 md:flex-row md:items-center md:justify-between md:border-0 md:bg-transparent md:p-0 print:hidden">
        <Link to={`/assessments/members/${memberId}?tab=${isAnthropometry ? "registro" : "bioimpedancia"}`} className="inline-flex items-center gap-2 text-sm font-medium text-lovable-ink-muted transition hover:text-lovable-ink">
          <ArrowLeft size={14} />
          {isAnthropometry ? "Voltar para antropometria" : "Voltar para bioimpedancia"}
        </Link>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="primary" onClick={() => void handleOpenPdf("technical")}>
            <Download size={14} />
            Abrir PDF
          </Button>
          {!isAnthropometry ? (
            <Button size="sm" variant="secondary" onClick={() => void handleOpenPdf("summary")}>
              <Download size={14} />
              Resumo do aluno
            </Button>
          ) : null}
          <Button size="sm" variant="secondary" onClick={() => window.print()}>
            <Printer size={14} />
            Imprimir
          </Button>
          <Button size="sm" variant="secondary" onClick={() => void handleShare()}>
            <Share2 size={14} />
            Compartilhar
          </Button>
        </div>
      </div>

      <ErrorBoundary
        fallback={(
          <Card>
            <CardContent className="space-y-4 pt-6">
              <div>
                <h1 className="text-xl font-semibold text-lovable-ink">Relatorio da avaliacao</h1>
                <p className="mt-1 text-sm text-lovable-ink-muted">
                  Uma parte visual nao pode ser exibida, mas o relatorio completo continua disponivel em PDF.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="primary" onClick={() => void handleOpenPdf("technical")}>
                  <Download size={14} />
                  Abrir PDF
                </Button>
                <Link to={`/assessments/members/${memberId}?tab=${isAnthropometry ? "registro" : "bioimpedancia"}`}>
                  <Button variant="secondary">Voltar para a avaliacao</Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        )}
      >
        <article className="clinical-web-document body-composition-report-document mx-auto max-w-[1180px] overflow-hidden rounded-[30px] border border-[#d2ccc4] bg-[#fcfbf7] text-[#15110f] shadow-[0_24px_60px_rgba(0,0,0,0.18)] print:overflow-visible print:rounded-none print:border-none print:bg-white print:shadow-none">
          <div className="body-composition-report-content">
          {isSemanticV2 ? (
            <SemanticReportV2 report={report} header={reportHeader} isAnthropometry={isAnthropometry} />
          ) : (
          <>
          <section className="clinical-web-page">
            {isAnthropometry ? (
              <p className="mb-3 inline-flex rounded-full border border-[#157ca5]/30 bg-[#eaf6fa] px-3 py-1 text-xs font-bold uppercase tracking-[0.14em] text-[#0b668a]">
                Antropometria — sem bioimpedancia
              </p>
            ) : null}
            <ReportHeader
              header={reportHeader}
              physicalAge={metricValue(physicalAgeMetric)}
              bmr={metricValue(bmrMetric)}
              basalMetabolicRateOriginLabel={metricOriginLabel(bmrMetric, report.basal_metabolic_rate_origin)}
              muscleMassOriginLabel={metricOriginLabel(muscleMassMetric, report.muscle_mass_origin)}
            />
            <section className="clinical-web-page-grid">
              <SummaryCard score={reportScore} insight={leadInsight} />
              <KeyIndicatorsTable
                metrics={keyIndicators}
                context={report.body_fat_context ?? null}
                origins={report}
              />
            </section>
            <CompositionDetailGrid
              metrics={detailMetrics}
              context={report.body_fat_context ?? null}
              origins={report}
            />
          </section>

          <section className="clinical-web-page">
            <ReportMiniHeader header={reportHeader} />
            <MeasurementsSection rows={measurementRows} sex={reportHeader.sex} conservative />
            <section className="clinical-web-page-grid clinical-web-late-grid">
              <GoalCards metrics={cleanGoalMetrics} />
              <BodyFatSourcePanel context={report.body_fat_context ?? null} />
            </section>
            <LegacyComparisonNotice />
            <ClientObservations insights={[]} teacherNotes={report.teacher_notes} />
          </section>
          </>
          )}
          </div>
        </article>
      </ErrorBoundary>
    </section>
  );
}

export default BodyCompositionReportPage;

function SemanticReportV2({
  report,
  header,
  isAnthropometry,
}: {
  report: BodyCompositionReport;
  header: BodyCompositionReportHeader;
  isAnthropometry: boolean;
}) {
  const metrics = [...(report.metrics ?? [])].sort((a, b) => a.display_order - b.display_order);
  const role = (name: BodyCompositionReportMetric["display_roles"][number]) =>
    metrics.filter((metric) => metric.display_roles.includes(name) && metric.current.value != null);
  const headlines = role("headline").slice(0, 5);
  const indicators = role("key_indicator");
  const details = role("composition_detail");
  const measurements = role("body_measurement").map((metric): BodyCompositionMeasurementRow => ({
    key: metric.key,
    label: metric.label,
    current_value: metric.current.value,
    previous_value: metric.previous?.value ?? null,
    delta: metric.delta,
    unit: metric.current.unit ?? "",
    used_for_body_fat_calculation: false,
    formatted_current: metric.current.formatted_value,
    formatted_previous: metric.previous?.formatted_value ?? "-",
    formatted_delta: metric.formatted_delta ?? "-",
  }));
  const physicalAge = metrics.find((metric) => metric.key === "physical_age")?.current.formatted_value ?? "-";
  const bmr = metrics.find((metric) => ["basal_metabolic_rate_kcal", "bmr"].includes(metric.key));
  const comparisonMessages = Array.from(new Set(metrics
    .filter((metric) => metric.comparison_status !== "comparable" && metric.comparison_message)
    .map((metric) => metric.comparison_message as string)));
  const eligibleHistory = (report.history ?? []).filter((series) => series.chart_eligible);

  return (
    <>
      <section className="clinical-web-page">
        {isAnthropometry ? (
          <p className="mb-3 inline-flex rounded-full border border-[#157ca5]/30 bg-[#eaf6fa] px-3 py-1 text-xs font-bold uppercase tracking-[0.14em] text-[#0b668a]">
            Antropometria — sem bioimpedancia
          </p>
        ) : null}
        {report.date_consistency === "future_legacy" ? (
          <div className="mb-4 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">
            Registro histórico com data futura. Comparações e evolução foram desativadas.
          </div>
        ) : null}
        <ReportHeader
          header={header}
          physicalAge={physicalAge}
          bmr={bmr?.current.formatted_value ?? "-"}
          basalMetabolicRateOriginLabel={bmr?.current.source_label ?? "Fonte não informada"}
          muscleMassOriginLabel={metrics.find((metric) => metric.key === "muscle_mass_kg")?.current.source_label ?? "Fonte não informada"}
        />
        <SemanticHeadlineMetrics metrics={headlines} evaluationNumber={report.evaluation_number} />
        <section className="clinical-web-page-grid">
          <SemanticScore report={report} />
          <SemanticMetricTable metrics={indicators} title="Indicadores-chave" />
        </section>
        <SemanticAnalysis report={report} />
        <SemanticMetricDetails metrics={details} />
      </section>

      <section className="clinical-web-page">
        <ReportMiniHeader header={header} />
        <MeasurementsSection rows={measurements} sex={header.sex} />
        <SemanticGoals report={report} />
        <SemanticPriorities report={report} />
        <SemanticComparisonNotices messages={comparisonMessages} />
        {eligibleHistory.length > 0 ? <SemanticHistory series={eligibleHistory} /> : null}
        <section className="clinical-web-section clinical-web-observations">
          <ReportSectionTitle title="Observações do professor" subtitle="Registro escrito pelo profissional responsável." />
          <div className="clinical-web-note">
            <p>{report.teacher_notes || "Sem observações registradas nesta avaliação."}</p>
          </div>
        </section>
        <section className="clinical-web-section">
          <ReportSectionTitle title="Metodologia" subtitle="Critérios e limites deste relatório." />
          <p className="text-sm text-[#554d46]">{report.methodological_note}</p>
        </section>
      </section>
    </>
  );
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : String(value);
}

function reportDateLabel(header: BodyCompositionReportHeader): string {
  return header.measured_at ? formatDateTime(header.measured_at) : formatDate(header.evaluation_date);
}

function SemanticHeadlineMetrics({ metrics, evaluationNumber }: { metrics: BodyCompositionReportMetric[]; evaluationNumber?: number }) {
  if (metrics.length === 0) return null;
  return (
    <section className="clinical-web-detail-grid mt-4" aria-label="Destaques da avaliação">
      {metrics.map((metric) => (
        <article key={metric.key} className="clinical-web-detail-item">
          <div>
            <span>{metric.current.source_label || `Avaliação ${evaluationNumber ?? "-"}`}</span>
            <strong>{metric.label}</strong>
            <small>{metric.comparison_status === "comparable" && metric.formatted_delta ? metric.formatted_delta : metric.status_label}</small>
          </div>
          <em>{metric.current.formatted_value}</em>
        </article>
      ))}
    </section>
  );
}

function SemanticScore({ report }: { report: BodyCompositionReport }) {
  const score = report.score;
  if (!score) return null;
  return (
    <section className="clinical-web-score-card">
      <div>
        <p>Score de composição corporal</p>
        <strong>{score.value ?? "-"}</strong>
        <span>/100</span>
      </div>
      <article>
        <h3>{score.band_label || "Sem classificação"}</h3>
        {score.comparison_status === "comparable" && score.formatted_delta ? <p>{score.formatted_delta}</p> : null}
        {score.disclaimer ? <small>{score.disclaimer}</small> : null}
      </article>
    </section>
  );
}

function semanticReference(metric: BodyCompositionReportMetric): string {
  const range = metric.reference_min != null && metric.reference_max != null
    ? `${formatNumber(metric.reference_min)} – ${formatNumber(metric.reference_max)}${metric.current.unit ? ` ${metric.current.unit}` : ""}`
    : metric.reference_label || "Sem faixa";
  return metric.reference_source ? `${range} · ${metric.reference_source}` : range;
}

function SemanticMetricTable({ metrics, title }: { metrics: BodyCompositionReportMetric[]; title: string }) {
  if (metrics.length === 0) return null;
  return (
    <section className="clinical-web-section clinical-web-key-section">
      <ReportSectionTitle title={title} subtitle="Valores, fontes e referências definidos pela API." />
      <div className="clinical-web-table-wrap">
        <table>
          <thead><tr><th>Métrica</th><th>Fonte</th><th>Valor</th><th>Referência</th></tr></thead>
          <tbody>{metrics.map((metric) => (
            <tr key={metric.key}>
              <td><strong>{metric.label}</strong><span className={statusClass(metric.status)}>{metric.status_label}</span></td>
              <td><span className="clinical-web-source-pill">{metric.current.source_label || "Fonte não informada"}</span></td>
              <td><strong>{metric.current.formatted_value}</strong></td>
              <td>{semanticReference(metric)}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </section>
  );
}

function SemanticAnalysis({ report }: { report: BodyCompositionReport }) {
  if (!report.analysis_cordex) return null;
  return (
    <section className="clinical-web-section clinical-web-observations">
      <ReportSectionTitle title="Análise Cordex" subtitle="Leitura semântica gerada a partir de comparações válidas." />
      <div className="clinical-web-note"><p>{report.analysis_cordex}</p></div>
    </section>
  );
}

function SemanticMetricDetails({ metrics }: { metrics: BodyCompositionReportMetric[] }) {
  if (metrics.length === 0) return null;
  return (
    <section className="clinical-web-section clinical-web-detail-section">
      <ReportSectionTitle title="Composição corporal detalhada" subtitle="Cada valor conserva sua fonte e seu método." />
      <div className="clinical-web-detail-grid">{metrics.map((metric) => (
        <article key={metric.key} className="clinical-web-detail-item">
          <div>
            <span>{metric.current.source_label || "Fonte não informada"}</span>
            <strong>{metric.label}</strong>
            <small>{metric.current.method_label || metric.status_label}</small>
          </div>
          <em>{metric.current.formatted_value}</em>
        </article>
      ))}</div>
    </section>
  );
}

function SemanticGoals({ report }: { report: BodyCompositionReport }) {
  const goals = report.goals;
  if (!goals) return null;
  return (
    <section className="clinical-web-section clinical-web-goals-card">
      <ReportSectionTitle title="Metas do ciclo" subtitle={goals.professional_message} />
      <p className="mb-3 text-sm font-semibold text-[#7c3f19]">{goals.member_message}</p>
      {goals.values?.length ? <div>{goals.values.map((goal) => (
        <p key={goal.key}><span>{goal.label}</span><strong>{goal.formatted_value}</strong></p>
      ))}</div> : null}
    </section>
  );
}

function SemanticPriorities({ report }: { report: BodyCompositionReport }) {
  if (!report.priorities?.length) return null;
  return (
    <section className="clinical-web-section clinical-web-observations">
      <ReportSectionTitle title="Prioridades" subtitle="Orientações ordenadas pela API." />
      <div className="clinical-web-insight-grid">{report.priorities.map((priority) => (
        <article key={priority.key}><h3>{priority.title}</h3><p>{priority.detail}</p></article>
      ))}</div>
    </section>
  );
}

function SemanticComparisonNotices({ messages }: { messages: string[] }) {
  if (messages.length === 0) return null;
  return (
    <section className="clinical-web-section">
      <ReportSectionTitle title="Comparabilidade" subtitle="Motivos fornecidos pelo contrato do relatório." />
      {messages.map((message) => <p key={message} className="mb-2 text-sm text-[#554d46]">{message}</p>)}
    </section>
  );
}

function SemanticHistory({ series }: { series: NonNullable<BodyCompositionReport["history"]> }) {
  return (
    <section className="clinical-web-section clinical-web-history-card">
      <ReportSectionTitle title="Histórico" subtitle="Séries com ao menos uma avaliação anterior metodologicamente compatível." />
      <div className="clinical-web-table-wrap"><table><thead><tr><th>Série</th><th>Pontos comparáveis</th><th>Excluídos</th></tr></thead>
        <tbody>{series.map((item) => <tr key={item.key}><td>{item.label}</td><td>{item.points.length}</td><td>{item.excluded_points_count}</td></tr>)}</tbody>
      </table></div>
    </section>
  );
}

function LegacyComparisonNotice() {
  return (
    <section className="clinical-web-section clinical-web-history-card">
      <ReportSectionTitle title="Historico" subtitle="Compatibilidade defensiva para relatórios anteriores." />
      <p className="text-sm font-semibold text-[#554d46]">Comparação indisponível neste relatório antigo</p>
    </section>
  );
}

function ReportHeader({
  header,
  physicalAge,
  bmr,
  basalMetabolicRateOriginLabel,
  muscleMassOriginLabel,
}: {
  header: BodyCompositionReportHeader;
  physicalAge: string;
  bmr: string;
  basalMetabolicRateOriginLabel: string;
  muscleMassOriginLabel: string;
}) {
  return (
    <header className="clinical-web-header">
      <div className="clinical-web-logo-row">
        <img src={CORDEX_LOGO_SRC} alt="Cordex Gym OS" className="clinical-web-cordex-logo" />
        <img src={PROGYM_LOGO_SRC} alt="ProGym" className="clinical-web-gym-logo" />
        <div className="clinical-web-member-block">
          <p>Relatorio de avaliacao fisica</p>
          <h1>{header.member_name}</h1>
          <span>{header.trainer_name || "Professor nao informado"}</span>
          <span>{header.gym_name || "Academia nao informada"}</span>
        </div>
      </div>
      <section className="clinical-web-meta-grid">
        <MetaCell label="Altura" value={headerValue(header.height_cm, "cm")} />
        <MetaCell label="Peso" value={headerValue(header.weight_kg, "kg")} prominent />
        <MetaCell label="Idade" value={headerValue(header.age_years, "anos")} />
        <MetaCell label="Sexo" value={sexLabel(header.sex)} />
        <MetaCell label="Idade fisica" value={physicalAge} />
        <MetaCell label="Metab. basal" value={bmr} />
        <MetaCell label={header.measured_at ? "Data / hora" : "Data"} value={reportDateLabel(header)} />
      </section>
      <section className="mt-3 grid gap-2 sm:grid-cols-2" aria-label="Origem dos calculos">
        <div className="rounded-lg border border-[#d8d2ca] bg-[#f7f4ef] px-4 py-3">
          <span className="block text-[10px] font-bold uppercase tracking-[0.18em] text-[#7c6250]">Origem da TMB</span>
          <strong className="mt-1 block text-sm text-[#050505]">{basalMetabolicRateOriginLabel}</strong>
        </div>
        <div className="rounded-lg border border-[#d8d2ca] bg-[#f7f4ef] px-4 py-3">
          <span className="block text-[10px] font-bold uppercase tracking-[0.18em] text-[#7c6250]">Origem da massa muscular</span>
          <strong className="mt-1 block text-sm text-[#050505]">{muscleMassOriginLabel}</strong>
        </div>
      </section>
    </header>
  );
}

function ReportMiniHeader({ header }: { header: BodyCompositionReportHeader }) {
  return (
    <header className="clinical-web-mini-header">
      <img src={CORDEX_LOGO_SRC} alt="" aria-hidden="true" />
      <div>
        <p>Relatorio de avaliacao fisica</p>
        <strong>{header.member_name}</strong>
        <span>{reportDateLabel(header)}</span>
      </div>
    </header>
  );
}

function MetaCell({ label, value, prominent = false }: { label: string; value: string; prominent?: boolean }) {
  return (
    <div className={`clinical-web-meta-cell${prominent ? " clinical-web-meta-cell-prominent" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ReportSectionTitle({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="clinical-web-section-title">
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </div>
  );
}

function SummaryCard({ score, insight }: { score: string; insight: BodyCompositionInsight | null }) {
  return (
    <section className="clinical-web-score-card">
      <div>
        <p>Score da avaliacao</p>
        <strong>{score}</strong>
        <span>/100</span>
      </div>
      <article>
        <h3>Leitura da avaliacao</h3>
        <p>{insight?.message || "Acompanhe a evolucao comparando peso, medidas e frequencia nas proximas avaliacoes."}</p>
      </article>
    </section>
  );
}

function KeyIndicatorsTable({
  metrics,
  context,
  origins,
}: {
  metrics: BodyCompositionReferenceMetric[];
  context: BodyCompositionBodyFatContext | null;
  origins: ReportCalculationOrigins;
}) {
  if (metrics.length === 0) return null;
  return (
    <section className="clinical-web-section clinical-web-key-section">
      <ReportSectionTitle title="Indicadores-chave" subtitle="Indices principais para acompanhar a evolucao." />
      <div className="clinical-web-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Metrica</th>
              <th>Fonte</th>
              <th>Valor</th>
              <th>Faixa</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((metric) => (
              <tr key={metric.key}>
                <td>
                  <strong>{metric.label}</strong>
                  <span className={statusClass(metric.status)}>{metricStatusLabel(metric)}</span>
                </td>
                <td>
                  <span className="clinical-web-source-pill">{metricSource(metric, context, origins).label}</span>
                </td>
                <td>
                  <strong>{metric.formatted_value}</strong>
                </td>
                <td>{metricReference(metric)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function CompositionDetailGrid({
  metrics,
  context,
  origins,
}: {
  metrics: BodyCompositionReferenceMetric[];
  context: BodyCompositionBodyFatContext | null;
  origins: ReportCalculationOrigins;
}) {
  if (metrics.length === 0) return null;
  return (
    <section className="clinical-web-section clinical-web-detail-section">
      <ReportSectionTitle title="Composicao corporal detalhada" subtitle="Cada valor mostra a origem usada no relatorio." />
      <div className="clinical-web-detail-grid">
        {metrics.map((metric) => (
          <article key={metric.key} className="clinical-web-detail-item">
            <div>
              <span>{metricSource(metric, context, origins).label}</span>
              <strong>{metric.label}</strong>
              <small>{metricExplanation(metric, context, origins)}</small>
            </div>
            <em>{metric.formatted_value}</em>
          </article>
        ))}
      </div>
    </section>
  );
}

function BodyFatSourcePanel({ context }: { context: BodyCompositionBodyFatContext | null }) {
  if (!context) return null;
  return (
    <section className="clinical-web-body-fat-panel">
      <div>
        <p>Metodo de leitura da gordura corporal</p>
        <h2>{formatPercent(context.used_percent)}</h2>
        <span>{bodyFatPanelDescription(context.used_source)}</span>
      </div>
      <div className="clinical-web-body-fat-grid">
        <ContextMetric label="Fonte usada" value={sourceLabel(context.used_source)} />
        <ContextMetric label="Metodo" value={methodLabel(context.method)} />
      </div>
    </section>
  );
}

function ContextMetric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function MeasurementsSection({ rows, sex, conservative = false }: { rows: BodyCompositionMeasurementRow[]; sex: BodyCompositionSex | null; conservative?: boolean }) {
  const visibleRows = rows.filter((row) => row.current_value != null || row.previous_value != null);
  if (visibleRows.length === 0) return null;
  return (
    <section className="clinical-web-section clinical-web-measurement-section">
      <ReportSectionTitle title="Medidas corporais" subtitle="Mapa anatomico generico para localizar perimetria. Nao usa foto do aluno." />
      <MeasurementMap rows={visibleRows} sex={sex} conservative={conservative} />
    </section>
  );
}

function MeasurementMap({ rows, sex, conservative = false }: { rows: BodyCompositionMeasurementRow[]; sex: BodyCompositionSex | null; conservative?: boolean }) {
  const preferredOrder = [
    "neck_cm",
    "shoulders_cm",
    "chest_cm",
    "right_arm_relaxed_cm",
    "left_arm_relaxed_cm",
    "right_arm_flexed_cm",
    "left_arm_flexed_cm",
    "waist_cm",
    "abdomen_cm",
    "hip_cm",
    "right_thigh_cm",
    "left_thigh_cm",
    "right_calf_cm",
    "left_calf_cm",
  ];
  const orderedRows = [...rows].sort((a, b) => preferredOrder.indexOf(a.key) - preferredOrder.indexOf(b.key));
  const midpoint = Math.ceil(orderedRows.length / 2);
  const leftRows = orderedRows.slice(0, midpoint);
  const rightRows = orderedRows.slice(midpoint);
  const alt = sex === "female" ? "Mapa corporal frontal feminino de medidas" : "Mapa corporal frontal masculino de medidas";
  return (
    <div className="clinical-web-measurement-map">
      <div className="clinical-web-bubble-column">
        {leftRows.map((row) => (
          <MeasurementBubble key={row.key} row={row} conservative={conservative} />
        ))}
      </div>
      <img src={bodyMapAsset(sex)} alt={alt} />
      <div className="clinical-web-bubble-column clinical-web-bubble-column-right">
        {rightRows.map((row) => (
          <MeasurementBubble key={row.key} row={row} conservative={conservative} />
        ))}
      </div>
    </div>
  );
}

function MeasurementBubble({ row, conservative = false }: { row: BodyCompositionMeasurementRow; conservative?: boolean }) {
  const hasCurrent = row.current_value != null;
  const hasPrevious = !conservative && row.previous_value != null;
  const comparison = hasCurrent && hasPrevious
    ? `Anterior: ${row.formatted_previous}${row.formatted_delta !== "-" ? ` · ${row.formatted_delta}` : ""}`
    : hasCurrent
      ? "Primeira avaliação"
      : "Não aferido nesta avaliação";
  return (
    <article className="clinical-web-measurement-bubble">
      <span>{hasCurrent ? "Atual" : "Anterior"}</span>
      <strong>{row.label}</strong>
      <em>{hasCurrent ? row.formatted_current : (conservative ? "-" : row.formatted_previous)}</em>
      <small>{comparison}</small>
    </article>
  );
}

function GoalCards({ metrics }: { metrics: BodyCompositionReferenceMetric[] }) {
  if (metrics.length === 0) return null;
  return (
    <section className="clinical-web-side-card clinical-web-goals-card">
      <h3>Metas do ciclo</h3>
      <div>
        {metrics.map((metric) => (
          <p key={metric.key}>
            <span>{metric.label}</span>
            <strong>{metric.formatted_value}</strong>
          </p>
        ))}
      </div>
    </section>
  );
}

function ClientObservations({
  insights,
  teacherNotes,
}: {
  insights: BodyCompositionInsight[];
  teacherNotes: string | null;
}) {
  return (
    <section className="clinical-web-section clinical-web-observations">
      <ReportSectionTitle title="Observacoes" subtitle="Leitura simples para acompanhar a proxima etapa." />
      <div className="clinical-web-insight-grid">
        {insights.slice(0, 2).map((insight) => (
          <article key={insight.key}>
            <h3>{insight.title}</h3>
            <p>{insight.message}</p>
          </article>
        ))}
        {insights.length === 0 ? (
          <article>
            <h3>Historico em consolidacao</h3>
            <p>Acompanhe a evolucao comparando novas avaliacoes com as mesmas condicoes de medicao.</p>
          </article>
        ) : null}
      </div>
      {teacherNotes ? (
        <div className="clinical-web-note">
          <strong>Observacao do professor</strong>
          <p>{teacherNotes}</p>
        </div>
      ) : null}
    </section>
  );
}
