import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Download, Printer } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import toast from "react-hot-toast";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { Button, Card, CardContent } from "../../components/ui2";
import { bodyCompositionService } from "../../services/bodyCompositionService";
import type {
  BodyCompositionBodyFatContext,
  BodyCompositionComparisonRow,
  BodyCompositionHistorySeries,
  BodyCompositionInsight,
  BodyCompositionMeasurementRow,
  BodyCompositionMetricCard,
  BodyCompositionReferenceMetric,
  BodyCompositionReportHeader,
  BodyCompositionSex,
  BodyCompositionTrend,
} from "../../types";

const CORDEX_LOGO_SRC = "/brand/cordex-logo-report.png";
const PROGYM_LOGO_SRC = "/progym-logo.png";
const EMPTY_VALUES = new Set(["", "-", "--"]);

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function formatNumber(value: number | null | undefined, unit?: string | null): string {
  if (value == null || !Number.isFinite(value)) return "-";
  const abs = Math.abs(value);
  const digits = abs >= 100 ? 0 : abs >= 10 ? 1 : 1;
  const formatted = value.toLocaleString("pt-BR", {
    minimumFractionDigits: Number.isInteger(value) ? 0 : 1,
    maximumFractionDigits: digits,
  });
  return unit ? `${formatted} ${unit}` : formatted;
}

function formatSigned(value: number | null | undefined, unit?: string | null): string {
  if (value == null || !Number.isFinite(value)) return "-";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${formatNumber(value, unit)}`;
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
    const match = metrics.find((metric) => metric.key === key);
    if (match) return match;
  }
  return null;
}

function metricValue(metric: BodyCompositionMetricCard | BodyCompositionReferenceMetric | null | undefined): string {
  return isPresentMetric(metric) ? String(metric?.formatted_value) : "-";
}

function metricDelta(metric: BodyCompositionMetricCard): string {
  if (metric.delta_absolute == null && metric.delta_percent == null) return "Sem comparacao";
  const arrow = metric.trend === "up" ? "↑" : metric.trend === "down" ? "↓" : "→";
  return `${arrow} ${formatSigned(metric.delta_absolute, metric.unit)}`;
}

function sourceLabel(source: string | null | undefined): string {
  if (source === "anthropometry" || source === "manual_anthropometry") return "Medidas manuais";
  if (source === "manual_override") return "Informado manualmente";
  if (source === "geneos_composite") return "Metodo composto GeneOS";
  if (source === "bioimpedance") return "Bioimpedancia bruta";
  return "Fonte pendente";
}

function methodLabel(method: string | null | undefined): string {
  if (method === "geneos_composite") return "Navy + RFM";
  if (method === "navy_circumference") return "Navy por circunferencias";
  if (method === "skinfold_protocol") return "Protocolo de dobras";
  if (method === "rfm") return "RFM";
  if (method === "manual_override") return "Informado manualmente";
  if (method === "legacy_bioimpedance" || method === "bioimpedance") return "Bioimpedancia bruta";
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

function statusLabel(status: string | null | undefined): string {
  if (status === "low") return "Abaixo";
  if (status === "adequate") return "Normal";
  if (status === "high") return "Acima";
  return "Sem faixa";
}

function statusClass(status: string | null | undefined): string {
  if (status === "low") return "text-[#b45309]";
  if (status === "high") return "text-[#b91c1c]";
  if (status === "adequate") return "text-[#047857]";
  return "text-[#7a7168]";
}

function metricReference(metric: BodyCompositionReferenceMetric): string {
  if (metric.reference_min == null && metric.reference_max == null) return "Sem faixa";
  if (metric.reference_min != null && metric.reference_max != null) {
    return `${formatNumber(metric.reference_min)} - ${formatNumber(metric.reference_max)}${metric.unit ? ` ${metric.unit}` : ""}`;
  }
  if (metric.reference_min != null) return `>= ${formatNumber(metric.reference_min)}${metric.unit ? ` ${metric.unit}` : ""}`;
  return `<= ${formatNumber(metric.reference_max)}${metric.unit ? ` ${metric.unit}` : ""}`;
}

function metricExplanation(key: string): string {
  const labels: Record<string, string> = {
    body_water_kg: "Agua total estimada no corpo",
    body_water_percent: "Participacao da agua corporal no peso",
    protein_kg: "Componente ligado a preservacao muscular",
    inorganic_salt_kg: "Minerais estimados no exame",
    skeletal_muscle_kg: "Massa muscular esqueletica informada",
    muscle_mass_kg: "Massa muscular informada",
    body_fat_kg: "Gordura bruta da bioimpedancia",
    fat_mass_estimated_kg: "Massa de gordura estimada",
    fat_free_mass_kg: "Componentes livres de gordura",
    lean_mass_estimated_kg: "Massa livre estimada",
    basal_metabolic_rate_kcal: "Gasto basal estimado",
    physical_age: "Idade fisica informada no exame",
  };
  return labels[key] ?? "Indicador complementar da avaliacao";
}

function filterCompositionMetrics(metrics: BodyCompositionReferenceMetric[]): BodyCompositionReferenceMetric[] {
  const byKey = new Map(metrics.map((metric) => [metric.key, metric]));
  const hasEstimatedFatMass = isPresentMetric(byKey.get("fat_mass_estimated_kg"));
  const hasCanonicalFatFreeMass = isPresentMetric(byKey.get("fat_free_mass_kg"));
  return metrics.filter((metric) => {
    if (!isPresentMetric(metric)) return false;
    if (metric.key === "body_fat_kg" && hasEstimatedFatMass) return false;
    if (metric.key === "lean_mass_estimated_kg" && hasCanonicalFatFreeMass) return false;
    return true;
  });
}

function bodyMapAsset(sex: BodyCompositionSex | null | undefined): string {
  return sex === "female" ? "/body-maps/body-map-front-female.png" : "/body-maps/body-map-front-male.png";
}

function BodyCompositionReportPage() {
  const { memberId, evaluationId } = useParams<{ memberId: string; evaluationId: string }>();

  useEffect(() => {
    document.body.classList.add("body-composition-report-print");
    return () => document.body.classList.remove("body-composition-report-print");
  }, []);

  const reportQuery = useQuery({
    queryKey: ["body-composition-report", memberId, evaluationId],
    queryFn: () => bodyCompositionService.getReport(memberId ?? "", evaluationId ?? ""),
    enabled: Boolean(memberId && evaluationId),
    staleTime: 60 * 1000,
  });

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
  const allReferenceMetrics = [...report.composition_metrics, ...report.risk_metrics, ...report.goal_metrics, ...report.muscle_fat_metrics];
  const allCardMetrics = report.primary_cards;
  const scoreMetric = metricByKey([...report.risk_metrics, ...report.primary_cards], "health_score");
  const physicalAgeMetric = metricByKey(report.risk_metrics, "physical_age");
  const compositionMetrics = filterCompositionMetrics(report.composition_metrics);
  const obesityMetrics = report.risk_metrics.filter((metric) => ["bmi", "body_fat_used_percent", "visceral_fat_level", "waist_hip_ratio"].includes(metric.key) && isPresentMetric(metric));
  const additionalMetrics = [
    metricByKey(allReferenceMetrics, "fat_free_mass_kg"),
    metricByKey(allReferenceMetrics, "body_water_kg"),
    metricByKey(allReferenceMetrics, "protein_kg"),
    metricByKey(allCardMetrics, "basal_metabolic_rate_kcal", "bmr"),
    physicalAgeMetric,
  ].filter((metric): metric is BodyCompositionReferenceMetric | BodyCompositionMetricCard => Boolean(metric && isPresentMetric(metric)));
  const leadInsight = report.insights[0] ?? null;

  async function handleOpenPdf(kind: "summary" | "technical") {
    if (!memberId || !evaluationId) return;
    const popup = window.open("", "_blank");
    try {
      await bodyCompositionService.openPdf(memberId, evaluationId, kind, popup);
    } catch {
      toast.error(kind === "technical" ? "Nao foi possivel abrir o relatorio tecnico." : "Nao foi possivel abrir o resumo do aluno.");
    }
  }

  return (
    <section className="body-composition-report-page space-y-6 print:space-y-0">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between print:hidden">
        <Link to={`/assessments/members/${memberId}?tab=bioimpedancia`} className="inline-flex items-center gap-2 text-sm font-medium text-lovable-ink-muted transition hover:text-lovable-ink">
          <ArrowLeft size={14} />
          Voltar para bioimpedancia
        </Link>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="primary" onClick={() => void handleOpenPdf("technical")}>
            <Download size={14} />
            Abrir PDF
          </Button>
          <Button size="sm" variant="secondary" onClick={() => void handleOpenPdf("summary")}>
            <Download size={14} />
            Resumo do aluno
          </Button>
          <Button size="sm" variant="secondary" onClick={() => window.print()}>
            <Printer size={14} />
            Imprimir
          </Button>
        </div>
      </div>

      <article className="clinical-web-document body-composition-report-document mx-auto max-w-[1180px] overflow-hidden rounded-[30px] border border-[#d2ccc4] bg-[#fcfbf7] text-[#15110f] shadow-[0_24px_60px_rgba(0,0,0,0.18)] print:overflow-visible print:rounded-none print:border-none print:bg-white print:shadow-none">
        <div className="body-composition-report-content p-7 md:p-10 print:p-0">
          <ReportHeader header={report.header} physicalAge={metricValue(physicalAgeMetric)} />

          <ReportSectionTitle title="Resultados principais" subtitle="Comparacao com a avaliacao anterior quando houver base disponivel." />
          <section className="clinical-web-summary-grid">
            {report.primary_cards.map((metric) => (
              <PrimaryMetricCard key={metric.key} metric={metric} />
            ))}
          </section>

          <BodyFatSourcePanel context={report.body_fat_context ?? null} />

          <section className="clinical-web-cover-grid">
            <SummaryCard score={metricValue(scoreMetric)} insight={leadInsight} />
            <MetricList title="Dados adicionais" metrics={additionalMetrics} />
          </section>

          <CompositionTable metrics={compositionMetrics} />
          <MeasurementsSection rows={report.measurement_rows ?? []} sex={report.header.sex} />

          <section className="clinical-web-analysis-grid">
            <BandPanel title="Analise musculo-gordura" subtitle="Posicao de cada valor dentro da faixa de referencia." metrics={report.muscle_fat_metrics} />
            <BandPanel title="Indicadores de acompanhamento" subtitle="Indices calculados a partir do exame e das medidas." metrics={obesityMetrics} />
          </section>

          <section className="clinical-web-side-grid">
            <MetricList title="Controle de peso" metrics={report.goal_metrics} />
            <HistoryTable comparisonRows={report.comparison_rows} historySeries={report.history_series} />
          </section>

          <FinalReading insights={report.insights} teacherNotes={report.teacher_notes} methodologicalNote={report.methodological_note} />
        </div>
      </article>
    </section>
  );
}

export default BodyCompositionReportPage;

function ReportHeader({ header, physicalAge }: { header: BodyCompositionReportHeader; physicalAge: string }) {
  return (
    <header className="clinical-web-header">
      <div className="clinical-web-logo-row">
        <img src={CORDEX_LOGO_SRC} alt="Cordex Gym OS" className="clinical-web-cordex-logo" />
        <img src={PROGYM_LOGO_SRC} alt="ProGym" className="clinical-web-gym-logo" />
        <div className="clinical-web-member-block">
          <p>Relatorio de bioimpedancia</p>
          <h1>{header.member_name}</h1>
          <span>{header.trainer_name || "Professor nao informado"}</span>
          <span>{header.gym_name || "Academia nao informada"}</span>
        </div>
      </div>
      <section className="clinical-web-meta-grid">
        <MetaCell label="Altura" value={headerValue(header.height_cm, "cm")} />
        <MetaCell label="Idade" value={headerValue(header.age_years, "anos")} />
        <MetaCell label="Sexo" value={sexLabel(header.sex)} />
        <MetaCell label="Idade fisica" value={physicalAge} />
        <MetaCell label="Peso" value={headerValue(header.weight_kg, "kg")} />
        <MetaCell label="Data / hora" value={formatDateTime(header.measured_at)} wide />
      </section>
    </header>
  );
}

function MetaCell({ label, value, wide = false }: { label: string; value: string; wide?: boolean }) {
  return (
    <div className={wide ? "clinical-web-meta-cell clinical-web-meta-cell-wide" : "clinical-web-meta-cell"}>
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

function PrimaryMetricCard({ metric }: { metric: BodyCompositionMetricCard }) {
  return (
    <article className="clinical-web-primary-card">
      <p>{metric.label}</p>
      <strong>{metric.formatted_value}</strong>
      <span>{metricDelta(metric)}</span>
    </article>
  );
}

function BodyFatSourcePanel({ context }: { context: BodyCompositionBodyFatContext | null }) {
  if (!context) return null;
  const range = context.range_min != null || context.range_max != null ? `${formatPercent(context.range_min)} a ${formatPercent(context.range_max)}` : "-";
  const review = context.manual_review_required ? (context.manual_review_completed ? "Concluida" : "Obrigatoria") : "Nao exigida";
  return (
    <section className="clinical-web-body-fat-panel">
      <div>
        <p>Fonte oficial da gordura corporal</p>
        <h2>{formatPercent(context.used_percent)}</h2>
        <span>Percentual tratado como estimativa operacional, sem valor diagnostico clinico.</span>
      </div>
      <div className="clinical-web-body-fat-grid">
        <ContextMetric label="Fonte usada no relatorio" value={sourceLabel(context.used_source)} />
        <ContextMetric label="Metodo" value={methodLabel(context.method)} />
        <ContextMetric label="Confianca" value={confidenceLabel(context.confidence)} />
        <ContextMetric label="Faixa estimada" value={range} />
        <ContextMetric label="Bioimpedancia bruta" value={formatPercent(context.bioimpedance_raw_percent)} />
        <ContextMetric label="Antropometria" value={formatPercent(context.anthropometric_percent)} />
        <ContextMetric label="Diferenca entre fontes" value={formatPercent(context.difference_between_sources)} />
        <ContextMetric label="Revisao manual" value={review} />
      </div>
      {context.quality_flags.length > 0 ? (
        <div className="clinical-web-flags">
          {context.quality_flags.map((flag) => (
            <span key={flag}>{flag}</span>
          ))}
        </div>
      ) : null}
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

function SummaryCard({ score, insight }: { score: string; insight: BodyCompositionInsight | null }) {
  return (
    <section className="clinical-web-score-card">
      <div>
        <p>Resumo da avaliacao</p>
        <strong>{score}</strong>
        <span>/100 pontos</span>
      </div>
      <article>
        <h3>Leitura de acompanhamento</h3>
        <p>{insight?.message || "Acompanhe a evolucao comparando peso, medidas e frequencia nas proximas avaliacoes."}</p>
      </article>
    </section>
  );
}

function CompositionTable({ metrics }: { metrics: BodyCompositionReferenceMetric[] }) {
  return (
    <section className="clinical-web-section">
      <ReportSectionTitle title="Analise da composicao corporal" subtitle="Valores da bioimpedancia e medidas com faixas de referencia disponiveis." />
      <div className="clinical-web-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Componente</th>
              <th>Descricao</th>
              <th>Valor</th>
              <th>Faixa</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((metric) => (
              <tr key={metric.key}>
                <td>
                  <strong>{metric.label}</strong>
                  <span className={statusClass(metric.status)}>{statusLabel(metric.status)}</span>
                </td>
                <td>{metricExplanation(metric.key)}</td>
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

function MeasurementsSection({ rows, sex }: { rows: BodyCompositionMeasurementRow[]; sex: BodyCompositionSex | null }) {
  const visibleRows = rows.filter((row) => row.current_value != null || row.previous_value != null);
  if (visibleRows.length === 0) return null;
  return (
    <section className="clinical-web-section clinical-web-measurement-section">
      <ReportSectionTitle title="Medidas corporais" subtitle="Mapa anatomico generico para localizar perimetria. Nao usa foto do aluno." />
      <div className="clinical-web-measurement-layout">
        <MeasurementMap rows={visibleRows} sex={sex} />
        <div className="clinical-web-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Medida</th>
                <th>Atual</th>
                <th>Anterior</th>
                <th>Variacao</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row) => (
                <tr key={row.key}>
                  <td>{row.label}</td>
                  <td>{row.formatted_current}</td>
                  <td>{row.formatted_previous}</td>
                  <td>{row.formatted_delta}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function MeasurementMap({ rows, sex }: { rows: BodyCompositionMeasurementRow[]; sex: BodyCompositionSex | null }) {
  const leftKeys = new Set(["shoulders_cm", "right_arm_relaxed_cm", "right_arm_flexed_cm", "waist_cm", "hip_cm", "right_thigh_cm", "right_calf_cm"]);
  const leftRows = rows.filter((row) => leftKeys.has(row.key));
  const rightRows = rows.filter((row) => !leftKeys.has(row.key));
  const alt = sex === "female" ? "Mapa corporal frontal feminino de medidas" : "Mapa corporal frontal masculino de medidas";
  return (
    <div className="clinical-web-measurement-map">
      <div className="clinical-web-bubble-column">
        {leftRows.map((row) => (
          <MeasurementBubble key={row.key} row={row} />
        ))}
      </div>
      <img src={bodyMapAsset(sex)} alt={alt} />
      <div className="clinical-web-bubble-column clinical-web-bubble-column-right">
        {rightRows.map((row) => (
          <MeasurementBubble key={row.key} row={row} />
        ))}
      </div>
    </div>
  );
}

function MeasurementBubble({ row }: { row: BodyCompositionMeasurementRow }) {
  const hasCurrent = row.current_value != null;
  return (
    <article className="clinical-web-measurement-bubble">
      <span>{hasCurrent ? "Atual" : "Anterior"}</span>
      <strong>{row.label}</strong>
      <em>{hasCurrent ? row.formatted_current : row.formatted_previous}</em>
      {hasCurrent && row.formatted_previous !== "-" ? <small>ant. {row.formatted_previous}</small> : null}
    </article>
  );
}

function BandPanel({ title, subtitle, metrics }: { title: string; subtitle: string; metrics: BodyCompositionReferenceMetric[] }) {
  return (
    <section className="clinical-web-section">
      <ReportSectionTitle title={title} subtitle={subtitle} />
      <div className="clinical-web-band-list">
        {metrics.filter(isPresentMetric).map((metric) => (
          <BandRow key={metric.key} metric={metric} />
        ))}
      </div>
    </section>
  );
}

function BandRow({ metric }: { metric: BodyCompositionReferenceMetric }) {
  const marker = bandMarker(metric);
  return (
    <article className="clinical-web-band-row">
      <div>
        <strong>{metric.label}</strong>
        <span>{metric.formatted_value}</span>
      </div>
      <div className="clinical-web-band-track">
        {marker == null ? null : <i style={{ left: `calc(${marker}% - 3px)` }} />}
      </div>
      <span className={statusClass(metric.status)}>{statusLabel(metric.status)}</span>
    </article>
  );
}

function bandMarker(metric: BodyCompositionReferenceMetric): number | null {
  if (metric.value == null || metric.reference_min == null || metric.reference_max == null || metric.reference_max <= metric.reference_min) {
    return null;
  }
  const span = metric.reference_max - metric.reference_min;
  const expandedMin = metric.reference_min - span * 0.4;
  const expandedMax = metric.reference_max + span * 0.4;
  const percent = ((metric.value - expandedMin) / (expandedMax - expandedMin)) * 100;
  return Math.max(4, Math.min(96, percent));
}

function MetricList({ title, metrics }: { title: string; metrics: Array<BodyCompositionReferenceMetric | BodyCompositionMetricCard | null> }) {
  const visibleMetrics = metrics.filter((metric): metric is BodyCompositionReferenceMetric | BodyCompositionMetricCard => Boolean(metric && isPresentMetric(metric)));
  if (visibleMetrics.length === 0) return null;
  return (
    <section className="clinical-web-side-card">
      <h3>{title}</h3>
      <div>
        {visibleMetrics.map((metric) => (
          <p key={metric.key}>
            <span>{metric.label}</span>
            <strong>{metric.formatted_value}</strong>
          </p>
        ))}
      </div>
    </section>
  );
}

function HistoryTable({ comparisonRows, historySeries }: { comparisonRows: BodyCompositionComparisonRow[]; historySeries: BodyCompositionHistorySeries[] }) {
  const columns = Array.from(
    new Set(
      historySeries
        .flatMap((series) => series.points)
        .map((point) => point.evaluation_date)
        .filter(Boolean),
    ),
  ).slice(-2);
  const rows = comparisonRows.slice(0, 8);
  if (rows.length === 0 && columns.length === 0) return null;
  return (
    <section className="clinical-web-side-card clinical-web-history-card">
      <h3>Historico - Anterior x Atual</h3>
      <div className="clinical-web-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Metrica</th>
              <th>{columns[0] || "Anterior"}</th>
              <th>{columns[1] || "Atual"}</th>
              <th>Tendencia</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key}>
                <td>{row.label}</td>
                <td>{row.previous_formatted}</td>
                <td>{row.current_formatted}</td>
                <td>{trendLabel(row.trend)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function trendLabel(trend: BodyCompositionTrend): string {
  if (trend === "up") return "Subiu";
  if (trend === "down") return "Caiu";
  if (trend === "stable") return "Estavel";
  return "Sem base";
}

function FinalReading({
  insights,
  teacherNotes,
  methodologicalNote,
}: {
  insights: BodyCompositionInsight[];
  teacherNotes: string | null;
  methodologicalNote: string;
}) {
  return (
    <section className="clinical-web-section clinical-web-final-section">
      <ReportSectionTitle title="Leitura Final" subtitle="Resumo simples para acompanhamento da evolucao." />
      <div className="clinical-web-insight-grid">
        {insights.length > 0 ? (
          insights.map((insight) => (
            <article key={insight.key}>
              <h3>{insight.title}</h3>
              <p>{insight.message}</p>
            </article>
          ))
        ) : (
          <article>
            <h3>Historico em consolidacao</h3>
            <p>Acompanhe a evolucao comparando novas avaliacoes com as mesmas condicoes de medicao.</p>
          </article>
        )}
      </div>
      {teacherNotes ? (
        <div className="clinical-web-note">
          <strong>Observacao do professor</strong>
          <p>{teacherNotes}</p>
        </div>
      ) : null}
      <p className="clinical-web-method-note">{methodologicalNote}</p>
    </section>
  );
}
