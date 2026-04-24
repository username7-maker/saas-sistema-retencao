import {
  Activity,
  ArrowDown,
  ArrowRight,
  ArrowUp,
  BarChart3,
  ShieldAlert,
  Target,
  TrendingUp,
} from "lucide-react";

import type {
  BodyCompositionComparisonRow,
  BodyCompositionDataQualityFlag,
  BodyCompositionHistorySeries,
  BodyCompositionInsight,
  BodyCompositionMetricCard,
  BodyCompositionReferenceMetric,
  BodyCompositionReportHeader,
  BodyCompositionTrend,
} from "../../../types";
import { Badge } from "../../ui2";

const SECTION_SERIF = { fontFamily: 'Georgia, "Times New Roman", serif' } as const;

function trendIcon(trend: BodyCompositionTrend) {
  if (trend === "up") return <ArrowUp size={12} />;
  if (trend === "down") return <ArrowDown size={12} />;
  return <ArrowRight size={12} />;
}

function trendLabel(trend: BodyCompositionTrend) {
  if (trend === "up") return "Subiu";
  if (trend === "down") return "Desceu";
  if (trend === "stable") return "Estavel";
  return "Sem base";
}

function formatSexLabel(value: BodyCompositionReportHeader["sex"]) {
  if (value === "male") return "Masculino";
  if (value === "female") return "Feminino";
  return "-";
}

function statusLabel(status: BodyCompositionReferenceMetric["status"]) {
  if (status === "adequate") return "Normal";
  if (status === "low") return "Baixo";
  if (status === "high") return "Acima";
  return "Sem faixa";
}

function statusTone(status: BodyCompositionReferenceMetric["status"]) {
  if (status === "adequate") return "text-emerald-700";
  if (status === "low") return "text-amber-700";
  if (status === "high") return "text-rose-700";
  return "text-slate-500";
}

function flagLabel(flag: BodyCompositionDataQualityFlag) {
  if (flag === "missing_body_fat_percent") return "% gordura ausente";
  if (flag === "missing_muscle_mass") return "massa muscular ausente";
  if (flag === "suspect_bmi") return "IMC suspeito";
  if (flag === "ocr_low_confidence") return "OCR com baixa confianca";
  return "revisao manual";
}

function normalizeMetricLabel(label: string) {
  return label.replace("×", "x").replace("Ã—", "x");
}

function clamp(value: number, min = 0, max = 100) {
  return Math.min(max, Math.max(min, value));
}

function formatSignedNumber(value: number | null, unit: string | null) {
  if (value == null) return "Sem base";
  const formatted = `${value > 0 ? "+" : ""}${value.toFixed(1).replace(".", ",")}`;
  return unit ? `${formatted} ${unit}` : formatted;
}

function buildRangeModel(metric: BodyCompositionReferenceMetric) {
  const value = metric.value;
  const referenceMin = metric.reference_min;
  const referenceMax = metric.reference_max;

  if (value == null || referenceMin == null || referenceMax == null || referenceMax <= referenceMin) {
    return { marker: 50, lowLimit: 33, highLimit: 67 };
  }

  const span = referenceMax - referenceMin;
  const domainMin = Math.max(0, referenceMin - span * 0.9);
  const domainMax = referenceMax + span * 0.9;
  const marker = clamp(((value - domainMin) / (domainMax - domainMin)) * 100);
  const lowLimit = clamp(((referenceMin - domainMin) / (domainMax - domainMin)) * 100);
  const highLimit = clamp(((referenceMax - domainMin) / (domainMax - domainMin)) * 100);
  return { marker, lowLimit, highLimit };
}

function buildHistoryColumns(series: BodyCompositionHistorySeries[]) {
  const labels = Array.from(
    new Set(
      series
        .flatMap((item) => item.points)
        .slice(-6)
        .map((point) => point.evaluation_date),
    ),
  ).slice(-6);
  return labels;
}

function DocumentSection({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3 border-t border-[#d8d5d0] pt-4 first:border-t-0 first:pt-0">
      <div className="space-y-1">
        <h2 className="text-[34px] leading-none text-[#4f433a]" style={SECTION_SERIF}>
          {title}
        </h2>
        {subtitle ? <p className="text-sm text-[#6d655f]">{subtitle}</p> : null}
      </div>
      {children}
    </section>
  );
}

export function ReportHeaderCard({
  header,
  dataQualityFlags,
  parsingConfidence,
}: {
  header: BodyCompositionReportHeader;
  dataQualityFlags: BodyCompositionDataQualityFlag[];
  parsingConfidence: number | null;
}) {
  return (
    <header className="space-y-5 border-b border-[#b7422f] pb-5">
      <div className="flex flex-col justify-between gap-5 lg:flex-row">
        <div className="space-y-2">
          <p className="text-6xl font-black uppercase tracking-[-0.06em] text-[#b7422f]">AI GYM OS</p>
          <div className="h-1 w-56 bg-[#b7422f]" />
          <p className="max-w-xl text-sm leading-6 text-[#615750]">
            Relatorio premium de composicao corporal estruturado para acompanhamento tecnico, percepcao de valor e impressao limpa.
          </p>
        </div>
        <div className="space-y-1 text-left lg:text-right">
          <p className="text-[15px] uppercase tracking-[0.22em] text-[#7a6f68]">Relatorio de bioimpedancia</p>
          <h1 className="text-4xl font-semibold tracking-[-0.03em] text-[#14110f]">{header.member_name}</h1>
          <p className="text-sm text-[#5d554e]">{header.trainer_name || "Professor nao informado"}</p>
          <p className="text-sm text-[#5d554e]">{header.gym_name || "Academia nao informada"}</p>
        </div>
      </div>

      <div className="grid gap-0 border border-[#d8d5d0] bg-[#f7f5f1] sm:grid-cols-5">
        <HeaderDatum label="ID" value={header.member_name.slice(0, 12).toUpperCase()} />
        <HeaderDatum label="Altura" value={header.height_cm != null ? `${header.height_cm} cm` : "-"} />
        <HeaderDatum label="Idade" value={header.age_years != null ? `${header.age_years} anos` : "-"} />
        <HeaderDatum label="Sexo" value={formatSexLabel(header.sex)} />
        <HeaderDatum
          label="Data / Hora"
          value={new Date(header.measured_at).toLocaleString("pt-BR", {
            dateStyle: "short",
            timeStyle: "short",
          })}
          last
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {dataQualityFlags.map((flag) => (
          <Badge key={flag} variant="neutral" className="border-[#d8d5d0] bg-[#f7f5f1] text-[#554c45]">
            {flagLabel(flag)}
          </Badge>
        ))}
        {parsingConfidence != null ? (
          <Badge variant="neutral" className="border-[#d8d5d0] bg-[#f7f5f1] text-[#554c45]">
            OCR {Math.round(parsingConfidence * 100)}%
          </Badge>
        ) : null}
      </div>
    </header>
  );
}

function HeaderDatum({ label, value, last = false }: { label: string; value: string; last?: boolean }) {
  return (
    <div className={`space-y-1 p-4 ${last ? "" : "border-b border-[#d8d5d0] sm:border-b-0 sm:border-r"}`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#7a6f68]">{label}</p>
      <p className="text-base font-semibold text-[#171311]">{value}</p>
    </div>
  );
}

export function MetricHighlights({ metrics }: { metrics: BodyCompositionMetricCard[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
      {metrics.map((metric) => (
        <article key={metric.key} className="border border-[#d8d5d0] bg-[#faf8f4] px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#7a6f68]">{metric.label}</p>
          <p className="mt-2 text-3xl font-semibold text-[#15110f]">{metric.formatted_value}</p>
          <div className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-[#5f5852]">
            {trendIcon(metric.trend)}
            <span>{formatSignedNumber(metric.delta_absolute, metric.unit)}</span>
          </div>
        </article>
      ))}
    </div>
  );
}

export function CompositionAnalysisTable({ metrics }: { metrics: BodyCompositionReferenceMetric[] }) {
  return (
    <DocumentSection
      title="Analise da Composicao Corporal"
      subtitle="Leitura dos compartimentos corporais realmente disponiveis neste exame."
    >
      <div className="overflow-hidden border border-[#d8d5d0]">
        <table className="min-w-full border-collapse text-sm">
          <tbody>
            {metrics.map((metric, index) => (
              <tr key={metric.key} className={index % 2 === 0 ? "bg-[#f1efec]" : "bg-[#faf8f5]"}>
                <td className="w-[34%] border-r border-[#d8d5d0] px-4 py-3 text-[#655d56]">{compositionExplanation(metric.key)}</td>
                <td className="w-[33%] border-r border-[#d8d5d0] px-4 py-3">
                  <div className="flex items-center justify-between gap-4">
                    <span className="font-semibold text-[#1a1512]">{metric.label}</span>
                    <span className="text-[#6d655f]">{metric.unit || ""}</span>
                  </div>
                </td>
                <td className="w-[16%] border-r border-[#d8d5d0] px-4 py-3 text-right text-xl font-semibold text-[#171311]">
                  {metric.formatted_value}
                </td>
                <td className="px-4 py-3 text-right text-[#6d655f]">
                  {metric.reference_min != null || metric.reference_max != null
                    ? `(${metric.reference_min ?? "-"} ~ ${metric.reference_max ?? "-"})`
                    : "(sem faixa)"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DocumentSection>
  );
}

function compositionExplanation(key: string) {
  if (key === "body_water_kg") return "Quantidade total de agua no corpo";
  if (key === "protein_kg") return "Para a construcao e preservacao muscular";
  if (key === "inorganic_salt_kg") return "Para fortalecimento estrutural";
  if (key === "body_fat_kg") return "Reserva energetica atual";
  if (key === "fat_free_mass_kg") return "Componentes livres de gordura";
  if (key === "muscle_mass_kg") return "Base muscular do organismo";
  return "Leitura corporal";
}

export function BandAnalysisPanel({
  title,
  subtitle,
  metrics,
}: {
  title: string;
  subtitle?: string;
  metrics: BodyCompositionReferenceMetric[];
}) {
  return (
    <DocumentSection title={title} subtitle={subtitle}>
      <div className="space-y-4 border border-[#d8d5d0] bg-[#fbfaf7] p-4">
        <div className="grid grid-cols-[180px_1fr_120px] items-center gap-3 border-b border-[#d8d5d0] pb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#756b64]">
          <span>Metrica</span>
          <div className="grid grid-cols-3 text-center">
            <span>Abaixo</span>
            <span>Normal</span>
            <span>Acima</span>
          </div>
          <span className="text-right">Valor</span>
        </div>
        {metrics.map((metric) => (
          <BandAnalysisRow key={metric.key} metric={metric} />
        ))}
      </div>
    </DocumentSection>
  );
}

function BandAnalysisRow({ metric }: { metric: BodyCompositionReferenceMetric }) {
  const model = buildRangeModel(metric);

  return (
    <div className="grid grid-cols-[180px_1fr_120px] items-center gap-3">
      <div>
        <p className="font-semibold text-[#171311]">{normalizeMetricLabel(metric.label)}</p>
        <p className={`text-xs font-medium ${statusTone(metric.status)}`}>{statusLabel(metric.status)}</p>
      </div>
      <div className="space-y-2">
        <div className="grid grid-cols-3 overflow-hidden border border-[#d8d5d0] text-[11px] font-semibold uppercase tracking-[0.12em] text-[#8a8179]">
          <span className="border-r border-[#d8d5d0] bg-[#f5f3f0] py-1 text-center">Abaixo</span>
          <span className="border-r border-[#d8d5d0] bg-[#ece9e4] py-1 text-center">Normal</span>
          <span className="bg-[#f5f3f0] py-1 text-center">Acima</span>
        </div>
        <div className="relative h-4 overflow-hidden border border-[#d8d5d0] bg-[#f3f1ee]">
          <div className="absolute inset-y-0 left-0 bg-[#dad5cf]" style={{ width: `${model.lowLimit}%` }} />
          <div
            className="absolute inset-y-0 bg-[#b7c1cc]"
            style={{ left: `${model.lowLimit}%`, width: `${Math.max(model.highLimit - model.lowLimit, 8)}%` }}
          />
          <div className="absolute inset-y-0 right-0 bg-[#dad5cf]" style={{ width: `${100 - model.highLimit}%` }} />
          <div className="absolute inset-y-0 w-[2px] bg-[#111111]" style={{ left: `calc(${model.marker}% - 1px)` }} />
        </div>
        <div className="flex justify-between text-[11px] text-[#7a6f68]">
          <span>{metric.reference_min != null ? metric.reference_min : "-"}</span>
          <span>{metric.reference_max != null ? metric.reference_max : "-"}</span>
        </div>
      </div>
      <div className="text-right text-2xl font-semibold text-[#171311]">{metric.formatted_value}</div>
    </div>
  );
}

export function RightRailSummary({
  scoreMetric,
  goalMetrics,
  obesityMetrics,
  additionalMetrics,
  waistHipMetric,
  visceralMetric,
}: {
  scoreMetric: BodyCompositionReferenceMetric | BodyCompositionMetricCard | null;
  goalMetrics: BodyCompositionReferenceMetric[];
  obesityMetrics: BodyCompositionReferenceMetric[];
  additionalMetrics: BodyCompositionReferenceMetric[];
  waistHipMetric: BodyCompositionReferenceMetric | null;
  visceralMetric: BodyCompositionReferenceMetric | null;
}) {
  return (
    <aside className="space-y-5">
      <SidebarSection title="Pontuacao corporal">
        <div className="text-center">
          <p className="text-6xl font-semibold tracking-[-0.05em] text-[#171311]">
            {scoreMetric?.value != null ? Math.round(Number(scoreMetric.value)) : "--"}
            <span className="text-2xl font-medium text-[#6b625b]">/100</span>
          </p>
          <p className="mx-auto mt-3 max-w-xs text-sm leading-6 text-[#635a53]">
            Leitura sintese para acompanhamento da composicao corporal. Nao substitui avaliacao clinica.
          </p>
        </div>
      </SidebarSection>

      <SidebarSection title="Controle de Peso">
        <MetricList metrics={goalMetrics} />
      </SidebarSection>

      <SidebarSection title="Avaliacao de Obesidade">
        <StatusChecklist metrics={obesityMetrics} />
      </SidebarSection>

      {waistHipMetric ? (
        <SidebarSection title="Relacao Cintura-Quadril">
          <MiniGauge metric={waistHipMetric} />
        </SidebarSection>
      ) : null}

      {visceralMetric ? (
        <SidebarSection title="Nivel de Gordura Visceral">
          <MiniGauge metric={visceralMetric} />
        </SidebarSection>
      ) : null}

      <SidebarSection title="Dados adicionais">
        <MetricList metrics={additionalMetrics} />
      </SidebarSection>
    </aside>
  );
}

function SidebarSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-[#d8d5d0] pt-3">
      <h3 className="text-[18px] font-semibold text-[#1a1613]">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function MetricList({ metrics }: { metrics: BodyCompositionReferenceMetric[] }) {
  return (
    <div className="space-y-2">
      {metrics.map((metric) => (
        <div key={metric.key} className="flex items-center justify-between gap-4 text-sm">
          <span className="text-[#5e554e]">{normalizeMetricLabel(metric.label)}</span>
          <span className="font-semibold text-[#171311]">{metric.formatted_value}</span>
        </div>
      ))}
    </div>
  );
}

function StatusChecklist({ metrics }: { metrics: BodyCompositionReferenceMetric[] }) {
  return (
    <div className="space-y-3">
      {metrics.map((metric) => (
        <div key={metric.key} className="flex items-center justify-between gap-3 text-sm">
          <span className="font-medium text-[#201a16]">{normalizeMetricLabel(metric.label)}</span>
          <span className={`inline-flex items-center gap-2 font-semibold ${statusTone(metric.status)}`}>
            <span className="h-2.5 w-2.5 rounded-full bg-current" />
            {statusLabel(metric.status)}
          </span>
        </div>
      ))}
    </div>
  );
}

function MiniGauge({ metric }: { metric: BodyCompositionReferenceMetric }) {
  const model = buildRangeModel(metric);
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-4xl font-semibold tracking-[-0.04em] text-[#171311]">{metric.formatted_value}</p>
        <p className={`text-sm font-semibold ${statusTone(metric.status)}`}>{statusLabel(metric.status)}</p>
      </div>
      <div className="relative h-3 overflow-hidden border border-[#d8d5d0] bg-[#f2efea]">
        <div className="absolute inset-y-0 left-0 bg-[#d9d3cd]" style={{ width: `${model.lowLimit}%` }} />
        <div
          className="absolute inset-y-0 bg-[#bcc3cc]"
          style={{ left: `${model.lowLimit}%`, width: `${Math.max(model.highLimit - model.lowLimit, 8)}%` }}
        />
        <div className="absolute inset-y-0 right-0 bg-[#d9d3cd]" style={{ width: `${100 - model.highLimit}%` }} />
        <div className="absolute inset-y-0 w-[2px] bg-[#111111]" style={{ left: `calc(${model.marker}% - 1px)` }} />
      </div>
      <div className="flex justify-between text-[11px] text-[#7a6f68]">
        <span>{metric.reference_min ?? "-"}</span>
        <span>{metric.reference_max ?? "-"}</span>
      </div>
    </div>
  );
}

export function HistoryCompositionPanel({ series }: { series: BodyCompositionHistorySeries[] }) {
  const columns = buildHistoryColumns(series);

  return (
    <DocumentSection
      title="Historico da Composicao Corporal"
      subtitle="Serie recente das metricas mais relevantes nas avaliacoes anteriores."
    >
      <div className="overflow-hidden border border-[#d8d5d0] bg-[#fbfaf7]">
        <div
          className="grid border-b border-[#d8d5d0] bg-[#f0ece8] text-[11px] font-semibold uppercase tracking-[0.18em] text-[#7a6f68]"
          style={{ gridTemplateColumns: `180px repeat(${Math.max(columns.length, 1)}, minmax(0, 1fr))` }}
        >
          <div className="border-r border-[#d8d5d0] px-4 py-3">Metrica</div>
          {columns.length ? (
            columns.map((column) => (
              <div key={column} className="border-r border-[#d8d5d0] px-3 py-3 last:border-r-0">
                {new Date(`${column}T12:00:00`).toLocaleDateString("pt-BR")}
              </div>
            ))
          ) : (
            <div className="px-3 py-3">Sem base</div>
          )}
        </div>
        <div className="divide-y divide-[#d8d5d0]">
          {series.map((item) => (
            <HistoryRow key={item.key} series={item} columns={columns} />
          ))}
        </div>
      </div>
    </DocumentSection>
  );
}

function HistoryRow({ series, columns }: { series: BodyCompositionHistorySeries; columns: string[] }) {
  const pointMap = new Map(series.points.map((point) => [point.evaluation_date, point]));

  return (
    <div
      className="grid"
      style={{ gridTemplateColumns: `180px repeat(${Math.max(columns.length, 1)}, minmax(0, 1fr))` }}
    >
      <div className="border-r border-[#d8d5d0] px-4 py-4">
        <p className="font-semibold text-[#171311]">{normalizeMetricLabel(series.label)}</p>
        <p className="text-xs text-[#746a63]">{series.unit || "indice"}</p>
      </div>
      {columns.length ? (
        columns.map((column) => {
          const point = pointMap.get(column);
          return (
            <div key={column} className="border-r border-[#ebe6df] px-2 py-3 last:border-r-0">
              {point?.value != null ? (
                <div className="flex flex-col items-center justify-center gap-2 text-center">
                  <span className="h-3 w-3 rounded-full bg-[#12100e]" />
                  <span className="text-sm font-semibold text-[#171311]">{point.value.toFixed(1).replace(".", ",")}</span>
                </div>
              ) : (
                <div className="h-full min-h-14 rounded-md border border-dashed border-[#dfdad4]" />
              )}
            </div>
          );
        })
      ) : (
        <div className="px-4 py-4 text-sm text-[#7b716a]">Historico insuficiente para comparacao.</div>
      )}
    </div>
  );
}

export function ComparisonTable({ rows }: { rows: BodyCompositionComparisonRow[] }) {
  return (
    <DocumentSection title="Anterior x Atual" subtitle="Leitura comparativa da avaliacao anterior contra a leitura atual.">
      <div className="overflow-hidden border border-[#d8d5d0] bg-[#fbfaf7]">
        <table className="min-w-full border-collapse text-sm">
          <thead className="bg-[#f0ece8] text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-[#7a6f68]">
            <tr>
              <th className="border-r border-[#d8d5d0] px-4 py-3">Metrica</th>
              <th className="border-r border-[#d8d5d0] px-4 py-3">Anterior</th>
              <th className="border-r border-[#d8d5d0] px-4 py-3">Atual</th>
              <th className="border-r border-[#d8d5d0] px-4 py-3">Delta</th>
              <th className="px-4 py-3">Tendencia</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} className="border-t border-[#e6e0d9]">
                <td className="border-r border-[#ece8e2] px-4 py-3 font-semibold text-[#171311]">{row.label}</td>
                <td className="border-r border-[#ece8e2] px-4 py-3 text-[#5d544d]">{row.previous_formatted}</td>
                <td className="border-r border-[#ece8e2] px-4 py-3 text-[#171311]">{row.current_formatted}</td>
                <td className="border-r border-[#ece8e2] px-4 py-3 text-[#5d544d]">
                  {formatSignedNumber(row.difference_absolute, row.unit)}
                </td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-1 text-sm font-semibold text-[#463d37]">
                    {trendIcon(row.trend)}
                    {trendLabel(row.trend)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DocumentSection>
  );
}

export function InsightPanel({
  insights,
  teacherNotes,
  methodologicalNote,
}: {
  insights: BodyCompositionInsight[];
  teacherNotes: string | null;
  methodologicalNote: string;
}) {
  return (
    <DocumentSection title="Leitura Final" subtitle="Insights deterministcos e observacoes operacionais da avaliacao.">
      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-3">
          {insights.map((insight) => (
            <div
              key={insight.key}
              className={`border px-4 py-4 ${
                insight.tone === "positive"
                  ? "border-emerald-200 bg-emerald-50"
                  : insight.tone === "warning"
                    ? "border-amber-200 bg-amber-50"
                    : "border-[#d8d5d0] bg-[#fbfaf7]"
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="inline-flex items-center gap-2">
                  {insight.tone === "positive" ? (
                    <TrendingUp size={16} className="text-emerald-700" />
                  ) : insight.tone === "warning" ? (
                    <ShieldAlert size={16} className="text-amber-700" />
                  ) : (
                    <Activity size={16} className="text-slate-600" />
                  )}
                  <p className="font-semibold text-[#171311]">{insight.title}</p>
                </div>
                <Badge variant="neutral" className="border-[#d8d5d0] bg-white text-[#4f463f]">
                  {insight.tone === "positive" ? "Positivo" : insight.tone === "warning" ? "Atencao" : "Neutro"}
                </Badge>
              </div>
              <p className="mt-2 text-sm leading-6 text-[#5e554e]">{insight.message}</p>
              {insight.reasons.length ? (
                <ul className="mt-3 space-y-1 text-xs text-[#736a63]">
                  {insight.reasons.map((reason) => (
                    <li key={reason}>- {reason}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ))}
        </div>
        <div className="space-y-4">
          <div className="border border-[#d8d5d0] bg-[#fbfaf7] p-4">
            <div className="inline-flex items-center gap-2">
              <Target size={16} className="text-[#b7422f]" />
              <p className="font-semibold text-[#171311]">Observacoes do professor</p>
            </div>
            <p className="mt-3 text-sm leading-6 text-[#5f5650]">
              {teacherNotes || "Sem observacoes registradas nesta avaliacao."}
            </p>
          </div>
          <div className="border border-[#d8d5d0] bg-[#f7f5f2] p-4 text-xs leading-6 text-[#70675f]">
            {methodologicalNote}
          </div>
        </div>
      </div>
    </DocumentSection>
  );
}

export function EmptyStateSegmentalAnalysis() {
  return (
    <section className="border border-dashed border-[#d8d5d0] bg-[#faf8f5] p-6 text-center">
      <BarChart3 className="mx-auto h-5 w-5 text-[#7a7068]" />
      <p className="mt-3 font-semibold text-[#171311]">Analise segmentar indisponivel neste exame</p>
      <p className="mt-1 text-sm text-[#726960]">
        Esta secao permanece oculta ate existirem dados segmentares reais da maquina ou do fluxo de importacao.
      </p>
    </section>
  );
}
