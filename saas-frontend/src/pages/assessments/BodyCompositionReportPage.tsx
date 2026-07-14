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

function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date);
}

function formatNumber(value: number | null | undefined, unit?: string | null): string {
  if (value == null || !Number.isFinite(value)) return "-";
  const abs = Math.abs(value);
  const digits = abs >= 100 ? 0 : 1;
  const formatted = value.toLocaleString("pt-BR", {
    minimumFractionDigits: Number.isInteger(value) ? 0 : 1,
    maximumFractionDigits: digits,
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
    const match = metrics.find((metric) => metric.key === key);
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
  if (metric.reference_min == null && metric.reference_max == null) return "Sem faixa";
  if (metric.reference_min != null && metric.reference_max != null) {
    return `${formatNumber(metric.reference_min)} - ${formatNumber(metric.reference_max)}${metric.unit ? ` ${metric.unit}` : ""}`;
  }
  if (metric.reference_min != null) return `>= ${formatNumber(metric.reference_min)}${metric.unit ? ` ${metric.unit}` : ""}`;
  return `<= ${formatNumber(metric.reference_max)}${metric.unit ? ` ${metric.unit}` : ""}`;
}

function metricExplanation(key: string, context?: BodyCompositionBodyFatContext | null): string {
  if (key === "body_fat_used_percent") {
    if (context?.used_source === "bioimpedance") return "Leitura de gordura informada pela bioimpedancia";
    if (context?.used_source === "manual_override") return "Percentual informado pelo profissional";
    return "Estimativa por protocolo de dobras e medidas";
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
    muscle_mass_kg: "Massa muscular informada",
    fat_mass_estimated_kg: "Massa de gordura calculada pelo percentual oficial",
    fat_free_mass_kg: "Massa livre de gordura informada",
    lean_mass_estimated_kg: "Massa livre estimada pelo percentual oficial",
    basal_metabolic_rate_kcal: "Metabolismo basal informado no exame",
    physical_age: "Idade fisica informada no exame",
  };
  return labels[key] ?? "Indicador de acompanhamento";
}

function bodyFatPanelDescription(source: string | null | undefined): string {
  if (source === "bioimpedance") return "Percentual lido da bioimpedancia porque esta avaliacao nao tem dobras/medidas suficientes.";
  if (source === "manual_override") return "Percentual informado manualmente pelo profissional responsavel.";
  return "Percentual estimado por dobras e medidas conforme o protocolo selecionado.";
}

function metricSource(metric: BodyCompositionReferenceMetric, context: BodyCompositionBodyFatContext | null): { group: "bioimpedance" | "measurements"; label: string } {
  const usedSource = context?.used_source ?? null;
  if (["body_fat_used_percent", "fat_mass_estimated_kg", "lean_mass_estimated_kg"].includes(metric.key)) {
    if (usedSource === "bioimpedance") return { group: "bioimpedance", label: "Bioimpedancia" };
    if (usedSource === "manual_override") return { group: "measurements", label: "Manual" };
    return { group: "measurements", label: "Dobras e medidas" };
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

function trendLabel(trend: BodyCompositionTrend): string {
  if (trend === "up") return "Subiu";
  if (trend === "down") return "Caiu";
  if (trend === "stable") return "Estavel";
  return "Sem base";
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
  const scoreMetric = metricByKey([...report.risk_metrics, ...report.primary_cards], "health_score");
  const reportScore = report.score_total != null ? formatNumber(report.score_total) : metricValue(scoreMetric);
  const physicalAgeMetric = metricByKey(report.risk_metrics, "physical_age");
  const bmrMetric = metricByKey(report.primary_cards, "basal_metabolic_rate_kcal", "bmr");
  const leadInsight = report.insights[0] ?? null;
  const keyIndicators = [
    metricByKey(allReferenceMetrics, "bmi"),
    metricByKey(allReferenceMetrics, "body_fat_used_percent"),
    metricByKey(allReferenceMetrics, "visceral_fat_level"),
    metricByKey(allReferenceMetrics, "waist_hip_ratio"),
  ].filter((metric): metric is BodyCompositionReferenceMetric => Boolean(metric && isPresentMetric(metric)));
  const detailMetrics = filterCompositionMetrics(report.composition_metrics);
  const cleanGoalMetrics = report.goal_metrics.filter(isPresentMetric);

  async function handleOpenPdf(kind: "summary" | "technical") {
    if (!memberId || !evaluationId) return;
    const popup = window.open("", "_blank");
    try {
      await bodyCompositionService.openPdf(memberId, evaluationId, kind, popup);
    } catch {
      popup?.close();
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
        <div className="body-composition-report-content">
          <section className="clinical-web-page">
            <ReportHeader header={report.header} physicalAge={metricValue(physicalAgeMetric)} bmr={metricValue(bmrMetric)} />
            <section className="clinical-web-page-grid">
              <SummaryCard score={reportScore} insight={leadInsight} />
              <KeyIndicatorsTable metrics={keyIndicators} context={report.body_fat_context ?? null} />
            </section>
            <CompositionDetailGrid metrics={detailMetrics} context={report.body_fat_context ?? null} />
          </section>

          <section className="clinical-web-page">
            <ReportMiniHeader header={report.header} />
            <MeasurementsSection rows={report.measurement_rows ?? []} sex={report.header.sex} />
            <section className="clinical-web-page-grid clinical-web-late-grid">
              <GoalCards metrics={cleanGoalMetrics} />
              <BodyFatSourcePanel context={report.body_fat_context ?? null} />
            </section>
            <HistoryTable comparisonRows={report.comparison_rows} historySeries={report.history_series} />
            <ClientObservations insights={report.insights} teacherNotes={report.teacher_notes} />
          </section>
        </div>
      </article>
    </section>
  );
}

export default BodyCompositionReportPage;

function ReportHeader({
  header,
  physicalAge,
  bmr,
}: {
  header: BodyCompositionReportHeader;
  physicalAge: string;
  bmr: string;
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
        <MetaCell label="Idade" value={headerValue(header.age_years, "anos")} />
        <MetaCell label="Sexo" value={sexLabel(header.sex)} />
        <MetaCell label="Idade fisica" value={physicalAge} />
        <MetaCell label="Metab. basal" value={bmr} />
        <MetaCell label="Data" value={formatDate(header.measured_at)} />
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
        <span>{formatDate(header.measured_at)}</span>
      </div>
    </header>
  );
}

function MetaCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="clinical-web-meta-cell">
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

function KeyIndicatorsTable({ metrics, context }: { metrics: BodyCompositionReferenceMetric[]; context: BodyCompositionBodyFatContext | null }) {
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
                  <span className={statusClass(metric.status)}>{statusLabel(metric.status)}</span>
                </td>
                <td>
                  <span className="clinical-web-source-pill">{metricSource(metric, context).label}</span>
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

function CompositionDetailGrid({ metrics, context }: { metrics: BodyCompositionReferenceMetric[]; context: BodyCompositionBodyFatContext | null }) {
  if (metrics.length === 0) return null;
  return (
    <section className="clinical-web-section clinical-web-detail-section">
      <ReportSectionTitle title="Composicao corporal detalhada" subtitle="Cada valor mostra a origem usada no relatorio." />
      <div className="clinical-web-detail-grid">
        {metrics.map((metric) => (
          <article key={metric.key} className="clinical-web-detail-item">
            <div>
              <span>{metricSource(metric, context).label}</span>
              <strong>{metric.label}</strong>
              <small>{metricExplanation(metric.key, context)}</small>
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

function MeasurementsSection({ rows, sex }: { rows: BodyCompositionMeasurementRow[]; sex: BodyCompositionSex | null }) {
  const visibleRows = rows.filter((row) => row.current_value != null || row.previous_value != null);
  if (visibleRows.length === 0) return null;
  return (
    <section className="clinical-web-section clinical-web-measurement-section">
      <ReportSectionTitle title="Medidas corporais" subtitle="Mapa anatomico generico para localizar perimetria. Nao usa foto do aluno." />
      <MeasurementMap rows={visibleRows} sex={sex} />
    </section>
  );
}

function MeasurementMap({ rows, sex }: { rows: BodyCompositionMeasurementRow[]; sex: BodyCompositionSex | null }) {
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
    <section className="clinical-web-section clinical-web-history-card">
      <ReportSectionTitle title="Historico" subtitle="Anterior x atual para acompanhar tendencia." />
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
