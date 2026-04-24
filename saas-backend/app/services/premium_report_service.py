from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import escape
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Gym
from app.services.dashboard_service import (
    get_churn_dashboard,
    get_commercial_dashboard,
    get_executive_dashboard,
    get_financial_dashboard,
    get_growth_mom_dashboard,
    get_mrr_dashboard,
    get_operational_dashboard,
    get_retention_dashboard,
    get_weekly_summary,
)


DashboardReportType = str
ALLOWED_DASHBOARD_REPORTS = {"executive", "operational", "commercial", "financial", "retention", "consolidated"}


@dataclass(slots=True)
class PremiumReportBranding:
    gym_name: str | None = None
    gym_logo_url: str | None = None
    product_name: str = "AI GYM OS"


@dataclass(slots=True)
class PremiumReportMetric:
    label: str
    value: str
    hint: str | None = None
    tone: str = "neutral"


@dataclass(slots=True)
class PremiumReportNarrative:
    title: str
    body: str
    tone: str = "neutral"


@dataclass(slots=True)
class PremiumReportTable:
    title: str
    columns: list[str]
    rows: list[list[str]]
    caption: str | None = None


@dataclass(slots=True)
class PremiumReportChartPoint:
    label: str
    value: float


@dataclass(slots=True)
class PremiumReportChart:
    title: str
    points: list[PremiumReportChartPoint]
    unit: str | None = None
    insight: str | None = None


@dataclass(slots=True)
class PremiumReportAction:
    title: str
    detail: str | None = None


@dataclass(slots=True)
class PremiumReportSection:
    title: str
    subtitle: str | None = None
    metrics: list[PremiumReportMetric] = field(default_factory=list)
    narratives: list[PremiumReportNarrative] = field(default_factory=list)
    tables: list[PremiumReportTable] = field(default_factory=list)
    charts: list[PremiumReportChart] = field(default_factory=list)
    actions: list[PremiumReportAction] = field(default_factory=list)


@dataclass(slots=True)
class PremiumReportPayload:
    report_kind: str
    report_scope: str
    title: str
    subtitle: str | None
    generated_at: datetime
    generated_by: str | None
    version: str
    branding: PremiumReportBranding
    parameters: dict[str, Any]
    entity_id: str | None = None
    evaluation_id: str | None = None
    subject_name: str | None = None
    cover_summary: str | None = None
    sections: list[PremiumReportSection] = field(default_factory=list)
    footer_note: str | None = None


def _read_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_int(value: Any) -> str:
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def _format_currency(value: Any) -> str:
    number = _coerce_float(value)
    return f"R$ {number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_percent(value: Any) -> str:
    return f"{_coerce_float(value):.1f}%"


def _format_label(label: str) -> str:
    return label.replace("_", " ").strip().title()


def _resolve_branding(db: Session) -> PremiumReportBranding:
    gym = db.scalar(select(Gym).limit(1))
    if gym is None:
        return PremiumReportBranding()
    return PremiumReportBranding(gym_name=gym.name)


def build_dashboard_report_payload(
    db: Session,
    dashboard: DashboardReportType,
    *,
    generated_by: str | None = None,
) -> PremiumReportPayload:
    dashboard_key = dashboard.strip().lower()
    if dashboard_key not in ALLOWED_DASHBOARD_REPORTS:
        raise ValueError(f"Dashboard invalido: {dashboard}")

    branding = _resolve_branding(db)
    generated_at = datetime.now(tz=timezone.utc)
    report_title = f"Relatorio {dashboard_key.title()}" if dashboard_key != "consolidated" else "Board Pack Consolidado"
    report_subtitle = "Relatorio premium AI GYM OS"
    cover_summary = _build_cover_summary(db, dashboard_key)

    if dashboard_key == "executive":
        executive = get_executive_dashboard(db)
        sections = [
            _build_executive_section(
                executive,
                revenue_points=get_mrr_dashboard(db, months=6),
                churn_points=get_churn_dashboard(db, months=6),
                growth_points=get_growth_mom_dashboard(db, months=6),
                weekly_summary=get_weekly_summary(db),
            )
        ]
        cover_summary = _build_dashboard_cover_summary("executive", executive=executive)
    elif dashboard_key == "operational":
        operational = get_operational_dashboard(db, page=1, page_size=10)
        sections = [_build_operational_section(operational, weekly_summary=get_weekly_summary(db))]
        cover_summary = _build_dashboard_cover_summary("operational", operational=operational)
    elif dashboard_key == "commercial":
        commercial = get_commercial_dashboard(db)
        sections = [_build_commercial_section(commercial)]
        cover_summary = _build_dashboard_cover_summary("commercial", commercial=commercial)
    elif dashboard_key == "financial":
        financial = get_financial_dashboard(db)
        sections = [_build_financial_section(financial, growth_points=get_growth_mom_dashboard(db, months=6))]
        cover_summary = _build_dashboard_cover_summary("financial", financial=financial)
    elif dashboard_key == "retention":
        retention = get_retention_dashboard(db, red_page=1, yellow_page=1, page_size=10)
        sections = [_build_retention_section(retention)]
        cover_summary = _build_dashboard_cover_summary("retention", retention=retention)
    else:
        executive = get_executive_dashboard(db)
        operational = get_operational_dashboard(db, page=1, page_size=10)
        commercial = get_commercial_dashboard(db)
        financial = get_financial_dashboard(db)
        retention = get_retention_dashboard(db, red_page=1, yellow_page=1, page_size=10)
        revenue_points = get_mrr_dashboard(db, months=6)
        churn_points = get_churn_dashboard(db, months=6)
        growth_points = get_growth_mom_dashboard(db, months=6)
        weekly_summary = get_weekly_summary(db)
        sections = [
            _build_executive_section(
                executive,
                revenue_points=revenue_points,
                churn_points=churn_points,
                growth_points=growth_points,
                weekly_summary=weekly_summary,
            ),
            _build_operational_section(operational, weekly_summary=weekly_summary),
            _build_commercial_section(commercial),
            _build_financial_section(financial, growth_points=growth_points),
            _build_retention_section(retention),
        ]
        cover_summary = _build_dashboard_cover_summary(
            "consolidated",
            executive=executive,
            operational=operational,
            commercial=commercial,
            financial=financial,
            retention=retention,
        )

    return PremiumReportPayload(
        report_kind="dashboard",
        report_scope=dashboard_key,
        title=report_title,
        subtitle=report_subtitle,
        generated_at=generated_at,
        generated_by=generated_by,
        version="premium-v1",
        branding=branding,
        parameters={"dashboard": dashboard_key},
        cover_summary=cover_summary,
        sections=sections,
        footer_note="Documento premium gerado pelo AI GYM OS. Dados sujeitos ao recorte temporal e ao escopo do tenant.",
    )


def _build_cover_summary(db: Session, dashboard_key: str) -> str:
    if dashboard_key == "consolidated":
        return "Pacote consolidado para lideranca, reunindo indicadores de execucao, risco, receita e comercial em um unico material."
    return f"Leitura premium do painel {dashboard_key}, estruturada para impressao, compartilhamento e decisao mais rapida."


def _build_dashboard_cover_summary(
    dashboard_key: str,
    *,
    executive: Any | None = None,
    operational: Any | None = None,
    commercial: Any | None = None,
    financial: Any | None = None,
    retention: Any | None = None,
) -> str:
    if dashboard_key == "executive" and executive is not None:
        return (
            f"Base com {_format_int(_read_value(executive, 'active_members', 0))} alunos ativos, "
            f"{_format_currency(_read_value(executive, 'mrr', 0.0))} em MRR e churn atual de "
            f"{_format_percent(_read_value(executive, 'churn_rate', 0.0))}."
        )
    if dashboard_key == "operational" and operational is not None:
        return (
            f"Fila operacional com {_format_int(_read_value(operational, 'inactive_7d_total', 0))} alunos inativos "
            f"ha 7+ dias e {_format_int(_read_value(operational, 'birthday_today_total', 0))} aniversariantes no dia."
        )
    if dashboard_key == "commercial" and commercial is not None:
        pipeline = _read_value(commercial, "pipeline", {}) or {}
        return (
            f"Pipeline com {_format_int(sum(int(v) for v in pipeline.values()) if pipeline else 0)} oportunidades ativas, "
            f"CAC de {_format_currency(_read_value(commercial, 'cac', 0.0))} e "
            f"{_format_int(_read_value(commercial, 'stale_leads_total', 0))} leads sem resposta recente."
        )
    if dashboard_key == "financial" and financial is not None:
        revenue = list(_read_value(financial, "monthly_revenue", []) or [])
        current_revenue = _read_value(revenue[-1], "value", 0.0) if revenue else 0.0
        return (
            f"Receita mensal recente de {_format_currency(current_revenue)} com inadimplencia de "
            f"{_format_percent(_read_value(financial, 'delinquency_rate', 0.0))}."
        )
    if dashboard_key == "retention" and retention is not None:
        return (
            f"{_format_currency(_read_value(retention, 'mrr_at_risk', 0.0))} em receita sob risco, "
            f"com {_format_int(_read_value(_read_value(retention, 'red', {}), 'total', 0))} alunos na fila vermelha."
        )
    if dashboard_key == "consolidated":
        return (
            f"Board pack do periodo com {_format_currency(_read_value(executive, 'mrr', 0.0) if executive else 0.0)} em MRR, "
            f"{_format_currency(_read_value(retention, 'mrr_at_risk', 0.0) if retention else 0.0)} em risco e "
            f"{_format_int(_read_value(commercial, 'stale_leads_total', 0) if commercial else 0)} leads sem contato recente."
        )
    return _build_cover_summary(db=None, dashboard_key=dashboard_key)  # type: ignore[call-arg]


def _build_executive_section(
    data: Any,
    *,
    revenue_points: Sequence[Any],
    churn_points: Sequence[Any],
    growth_points: Sequence[Any],
    weekly_summary: Any,
) -> PremiumReportSection:
    risk = _read_value(data, "risk_distribution", {}) or {}
    active_members = _read_value(data, "active_members", 0)
    total_members = _read_value(data, "total_members", 0)
    active_ratio = (_coerce_float(active_members) / max(_coerce_float(total_members), 1.0)) * 100
    latest_growth = _coerce_float(_read_value(growth_points[-1], "growth_mom", 0.0)) if growth_points else 0.0
    return PremiumReportSection(
        title="Resumo executivo",
        subtitle="Visao geral do negocio com KPIs principais e distribuicao de risco.",
        metrics=[
            PremiumReportMetric("Total de alunos", _format_int(_read_value(data, "total_members", 0)), tone="neutral"),
            PremiumReportMetric("Ativos", _format_int(_read_value(data, "active_members", 0)), tone="positive"),
            PremiumReportMetric("Base ativa", _format_percent(active_ratio), tone="positive"),
            PremiumReportMetric("MRR", _format_currency(_read_value(data, "mrr", 0.0)), tone="positive"),
            PremiumReportMetric("Churn", _format_percent(_read_value(data, "churn_rate", 0.0)), tone="warning"),
            PremiumReportMetric("NPS medio", f"{_coerce_float(_read_value(data, 'nps_avg', 0.0)):.1f}", tone="neutral"),
            PremiumReportMetric("Check-ins semana", _format_int(_read_value(weekly_summary, "checkins_this_week", 0)), tone="neutral"),
        ],
        narratives=[
            PremiumReportNarrative(
                "Leitura",
                (
                    f"O painel executivo abre o ciclo com {_format_currency(_read_value(data, 'mrr', 0.0))} de receita recorrente, "
                    f"{_format_percent(_read_value(data, 'churn_rate', 0.0))} de churn e "
                    f"variacao de {latest_growth:+.1f}% no crescimento mais recente."
                ),
                tone="neutral",
            ),
            PremiumReportNarrative(
                "Pulso semanal",
                (
                    f"A semana registrou {_format_int(_read_value(weekly_summary, 'checkins_this_week', 0))} check-ins, "
                    f"com delta de {_read_value(weekly_summary, 'checkins_delta_pct', 0.0):+.1f}% frente a semana anterior."
                ),
                tone="positive" if _coerce_float(_read_value(weekly_summary, "checkins_delta_pct", 0.0)) >= 0 else "warning",
            ),
        ],
        charts=[
            PremiumReportChart(
                title="MRR recente",
                points=[
                    PremiumReportChartPoint(
                        label=_format_month_label(_read_value(point, "month", f"M{i+1}")),
                        value=_coerce_float(_read_value(point, "value", 0.0)),
                    )
                    for i, point in enumerate(revenue_points[-6:])
                ],
                unit="R$",
                insight="Serie curta para leitura rapida da recorrencia mensal.",
            ),
            PremiumReportChart(
                title="Churn recente",
                points=[
                    PremiumReportChartPoint(
                        label=_format_month_label(_read_value(point, "month", f"M{i+1}")),
                        value=_coerce_float(_read_value(point, "churn_rate", 0.0)),
                    )
                    for i, point in enumerate(churn_points[-6:])
                ],
                unit="%",
                insight="Curva mensal de perda de base usada como referencia para a lideranca.",
            ),
        ],
        tables=[
            PremiumReportTable(
                title="Distribuicao de risco",
                columns=["Faixa", "Alunos"],
                rows=[
                    ["Verde", _format_int(_read_value(risk, "green", 0))],
                    ["Amarelo", _format_int(_read_value(risk, "yellow", 0))],
                    ["Vermelho", _format_int(_read_value(risk, "red", 0))],
                ],
                caption="Distribuicao atual da base por severidade de risco.",
            )
        ],
        actions=[
            PremiumReportAction("Revisar faixa vermelha", "Priorizar os alunos de maior risco nas proximas 24 horas."),
            PremiumReportAction("Confrontar MRR e churn", "Usar retencao e financeiro como complemento para leitura da pressao real de receita."),
        ],
    )


def _build_operational_section(data: Any, *, weekly_summary: Any) -> PremiumReportSection:
    inactive_items = list(_read_value(data, "inactive_7d_items", []) or [])[:5]
    birthday_items = list(_read_value(data, "birthday_today_items", []) or [])[:5]
    heatmap = list(_read_value(data, "heatmap", []) or [])
    peak_hours = _aggregate_peak_hours(heatmap)[:6]
    return PremiumReportSection(
        title="Operacao",
        subtitle="Leitura operacional com inatividade e pressao de execucao imediata.",
        metrics=[
            PremiumReportMetric("Check-ins ultima hora", _format_int(_read_value(data, "realtime_checkins", 0)), tone="neutral"),
            PremiumReportMetric("Inativos 7+ dias", _format_int(_read_value(data, "inactive_7d_total", 0)), tone="warning"),
            PremiumReportMetric("Aniversariantes hoje", _format_int(_read_value(data, "birthday_today_total", 0)), tone="positive"),
            PremiumReportMetric("Novos cadastros na semana", _format_int(_read_value(weekly_summary, "new_registrations", 0)), tone="neutral"),
        ],
        charts=[
            PremiumReportChart(
                title="Janelas de pico",
                points=[
                    PremiumReportChartPoint(label=str(point["label"]), value=_coerce_float(point["value"]))
                    for point in peak_hours
                ],
                unit="check-ins",
                insight="Faixas horarias com maior concentracao recente de check-ins.",
            )
        ]
        if peak_hours
        else [],
        tables=[
            PremiumReportTable(
                title="Top inativos",
                columns=["Aluno", "Risco", "Ultimo check-in"],
                rows=[
                    [
                        str(_read_value(item, "full_name", "?")),
                        str(_read_value(_read_value(item, "risk_level", "-"), "value", _read_value(item, "risk_level", "-"))),
                        _format_dateish(_read_value(item, "last_checkin_at")),
                    ]
                    for item in inactive_items
                ] or [["-", "-", "-"]],
                caption="Alunos com maior necessidade de acao operacional imediata.",
            ),
            PremiumReportTable(
                title="Aniversariantes do dia",
                columns=["Aluno", "Plano"],
                rows=[
                    [
                        str(_read_value(item, "full_name", "?")),
                        str(_read_value(item, "plan_name", "-")),
                    ]
                    for item in birthday_items
                ] or [["-", "-"]],
                caption="Recorte rapido para acao de relacionamento no dia.",
            ),
        ],
        narratives=[
            PremiumReportNarrative(
                "Leitura",
                (
                    f"A operacao premium concentra {_format_int(_read_value(data, 'inactive_7d_total', 0))} alunos sem check-in ha 7+ dias "
                    f"e {_format_int(_read_value(data, 'birthday_today_total', 0))} oportunidades de relacionamento imediato."
                ),
            )
        ],
        actions=[
            PremiumReportAction("Atacar inativos", "Usar playbooks de retencao e tarefas para reduzir o backlog de alunos sem check-in."),
            PremiumReportAction("Aproveitar aniversarios", "Converter o recorte do dia em contato de proximidade e oportunidade comercial."),
        ],
    )


def _build_commercial_section(data: Any) -> PremiumReportSection:
    pipeline = _read_value(data, "pipeline", {}) or {}
    conversions = list(_read_value(data, "conversion_by_source", []) or [])[:5]
    stale_leads = list(_read_value(data, "stale_leads", []) or [])[:5]
    return PremiumReportSection(
        title="Comercial",
        subtitle="Pipeline, CAC e conversao por origem em um material pronto para lideranca.",
        metrics=[
            PremiumReportMetric("CAC", _format_currency(_read_value(data, "cac", 0.0)), tone="warning"),
            PremiumReportMetric("Etapas no pipeline", _format_int(sum(int(v) for v in pipeline.values()) if pipeline else 0), tone="neutral"),
            PremiumReportMetric("Leads sem resposta", _format_int(_read_value(data, "stale_leads_total", 0)), tone="warning"),
        ],
        charts=[
            PremiumReportChart(
                title="Conversao por origem",
                points=[
                    PremiumReportChartPoint(
                        label=str(_read_value(row, "source", "?")),
                        value=_coerce_float(_read_value(row, "conversion_rate", 0.0)),
                    )
                    for row in conversions
                ],
                unit="%",
                insight="Comparativo entre fontes para orientar verba e follow-up.",
            )
        ]
        if conversions
        else [],
        tables=[
            PremiumReportTable(
                title="Pipeline atual",
                columns=["Etapa", "Total"],
                rows=[[str(stage), _format_int(total)] for stage, total in sorted(pipeline.items())] or [["-", "0"]],
            ),
            PremiumReportTable(
                title="Conversao por origem",
                columns=["Origem", "Conversao", "Won/Total"],
                rows=[
                    [
                        str(_read_value(row, "source", "?")),
                        _format_percent(_read_value(row, "conversion_rate", 0.0)),
                        f"{_format_int(_read_value(row, 'won', 0))}/{_format_int(_read_value(row, 'total', 0))}",
                    ]
                    for row in conversions
                ] or [["-", "0,0%", "0/0"]],
            ),
            PremiumReportTable(
                title="Leads sem resposta",
                columns=["Lead", "Estagio", "Ultimo contato"],
                rows=[
                    [
                        str(_read_value(row, "full_name", "?")),
                        _format_label(str(_read_value(row, "stage", "-"))),
                        _format_dateish(_read_value(row, "last_contact_at")),
                    ]
                    for row in stale_leads
                ] or [["-", "-", "Sem registro"]],
            ),
        ],
        narratives=[
            PremiumReportNarrative(
                "Leitura",
                (
                    f"O recorte comercial combina pipeline ativo, CAC de {_format_currency(_read_value(data, 'cac', 0.0))} "
                    f"e {_format_int(_read_value(data, 'stale_leads_total', 0))} leads sem resposta para orientar a proxima rodada de follow-up."
                ),
            )
        ],
        actions=[
            PremiumReportAction("Revisar origem lider", "Replicar discurso e cadencia da origem com melhor conversao relativa."),
            PremiumReportAction("Atacar leads estagnados", "Redistribuir ou reaquecer os leads parados antes de ampliar o topo do funil."),
        ],
    )


def _build_financial_section(data: Any, *, growth_points: Sequence[Any]) -> PremiumReportSection:
    revenue_points = list(_read_value(data, "monthly_revenue", []) or [])[-6:]
    projections = list(_read_value(data, "projections", []) or [])
    latest_growth = _coerce_float(_read_value(growth_points[-1], "growth_mom", 0.0)) if growth_points else 0.0
    chart_points = [
        PremiumReportChartPoint(
            label=_format_month_label(_read_value(point, "month", f"M{i+1}")),
            value=_coerce_float(_read_value(point, "value", 0.0)),
        )
        for i, point in enumerate(revenue_points)
    ]
    return PremiumReportSection(
        title="Financeiro",
        subtitle="Receita, inadimplencia e projecoes com leitura executiva compacta.",
        metrics=[
            PremiumReportMetric("Inadimplencia", _format_percent(_read_value(data, "delinquency_rate", 0.0)), tone="warning"),
            PremiumReportMetric(
                "Receita mensal atual",
                _format_currency(_read_value(revenue_points[-1], "value", 0.0) if revenue_points else 0.0),
                tone="positive",
            ),
            PremiumReportMetric("Crescimento mais recente", _format_percent(latest_growth), tone="neutral"),
        ],
        narratives=[
            PremiumReportNarrative(
                "Leitura",
                (
                    f"A visao financeira destaca inadimplencia de {_format_percent(_read_value(data, 'delinquency_rate', 0.0))} "
                    f"e crescimento mensal mais recente de {_format_percent(latest_growth)}."
                ),
                tone="neutral",
            )
        ],
        charts=[
            PremiumReportChart(
                title="Receita mensal recente",
                points=chart_points,
                unit="R$",
                insight="Serie recente de receita usada como referencia para o board pack.",
            )
        ],
        tables=[
            PremiumReportTable(
                title="Projecoes",
                columns=["Horizonte", "Receita projetada"],
                rows=[
                    [
                        f"{_format_int(_read_value(item, 'horizon_months', 0))} meses",
                        _format_currency(_read_value(item, "projected_revenue", 0.0)),
                    ]
                    for item in projections
                ] or [["-", _format_currency(0)]],
            )
        ],
        actions=[
            PremiumReportAction("Cruzar risco e receita", "Usar o recorte de retencao para validar a pressao de receita em risco."),
        ],
    )


def _build_retention_section(data: Any) -> PremiumReportSection:
    red = _read_value(data, "red", {}) or {}
    yellow = _read_value(data, "yellow", {}) or {}
    top_red = list(_read_value(red, "items", []) or [])[:5]
    top_yellow = list(_read_value(yellow, "items", []) or [])[:5]
    nps_trend = list(_read_value(data, "nps_trend", []) or [])[-6:]
    churn_distribution = _read_value(data, "churn_distribution", {}) or {}
    return PremiumReportSection(
        title="Retencao",
        subtitle="Leitura premium do risco, com fila critica e foco na recuperacao de base.",
        metrics=[
            PremiumReportMetric("Risco vermelho", _format_int(_read_value(red, "total", 0)), tone="negative"),
            PremiumReportMetric("Risco amarelo", _format_int(_read_value(yellow, "total", 0)), tone="warning"),
            PremiumReportMetric("MRR em risco", _format_currency(_read_value(data, "mrr_at_risk", 0.0)), tone="warning"),
            PremiumReportMetric("Score medio vermelho", f"{_coerce_float(_read_value(data, 'avg_red_score', 0.0)):.1f}", tone="negative"),
        ],
        charts=[
            PremiumReportChart(
                title="Curva de NPS",
                points=[
                    PremiumReportChartPoint(
                        label=_format_month_label(_read_value(point, "month", f"M{i+1}")),
                        value=_coerce_float(_read_value(point, "average_score", 0.0)),
                    )
                    for i, point in enumerate(nps_trend)
                ],
                unit="pts",
                insight="Serie recente de satisfacao para leitura junto com a pressao de risco.",
            ),
            PremiumReportChart(
                title="Distribuicao por tipo de churn",
                points=[
                    PremiumReportChartPoint(label=_format_label(str(label)), value=_coerce_float(total))
                    for label, total in sorted(churn_distribution.items())
                ],
                unit="alunos",
                insight="Agrupamento da base em risco por padrao predominante de churn.",
            ),
        ],
        tables=[
            PremiumReportTable(
                title="Top risco vermelho",
                columns=["Aluno", "Score", "Plano"],
                rows=[
                    [
                        str(_read_value(member, "full_name", "?")),
                        _format_int(_read_value(member, "risk_score", 0)),
                        str(_read_value(member, "plan_name", "-")),
                    ]
                    for member in top_red
                ] or [["-", "0", "-"]],
            ),
            PremiumReportTable(
                title="Fila amarela prioritária",
                columns=["Aluno", "Score", "Plano"],
                rows=[
                    [
                        str(_read_value(member, "full_name", "?")),
                        _format_int(_read_value(member, "risk_score", 0)),
                        str(_read_value(member, "plan_name", "-")),
                    ]
                    for member in top_yellow
                ] or [["-", "0", "-"]],
            ),
        ],
        narratives=[
            PremiumReportNarrative(
                "Leitura",
                (
                    f"O relatorio de retencao concentra {_format_currency(_read_value(data, 'mrr_at_risk', 0.0))} sob risco "
                    f"e os primeiros nomes que exigem resposta operacional no dia."
                ),
            )
        ],
        actions=[
            PremiumReportAction("Priorizar alto risco", "Executar follow-up e playbooks sobre a fila vermelha antes de ampliar a fila amarela."),
            PremiumReportAction("Atuar por padrao de churn", "Usar a distribuicao de churn para modular a mensagem e o canal de recuperacao."),
        ],
    )


def _aggregate_peak_hours(heatmap: Sequence[Any]) -> list[dict[str, Any]]:
    totals: dict[int, int] = {}
    for point in heatmap:
        hour_bucket = int(_read_value(point, "hour_bucket", 0) or 0)
        totals[hour_bucket] = totals.get(hour_bucket, 0) + int(_read_value(point, "total_checkins", 0) or 0)
    ordered = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    return [{"label": f"{hour:02d}h", "value": total} for hour, total in ordered]


def _format_month_label(label: Any) -> str:
    raw = str(label or "").strip()
    if len(raw) == 7 and raw[4] == "-":
        year, month = raw.split("-")
        month_map = {
            "01": "Jan",
            "02": "Fev",
            "03": "Mar",
            "04": "Abr",
            "05": "Mai",
            "06": "Jun",
            "07": "Jul",
            "08": "Ago",
            "09": "Set",
            "10": "Out",
            "11": "Nov",
            "12": "Dez",
        }
        return f"{month_map.get(month, month)}/{year[-2:]}"
    return raw or "-"


def _format_dateish(value: Any) -> str:
    if value is None:
        return "Sem registro"
    if isinstance(value, str):
        return value[:10]
    if hasattr(value, "date"):
        return value.date().isoformat()
    return str(value)


def render_premium_report_html(payload: PremiumReportPayload) -> str:
    if payload.report_kind == "body_composition":
        return _render_body_composition_report_html(payload)

    sections_html = "".join(_render_section(section) for section in payload.sections)
    generated_label = payload.generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    generated_by = escape(payload.generated_by or "Sistema")
    gym_name = escape(payload.branding.gym_name or "Academia")
    title = escape(payload.title)
    subtitle = escape(payload.subtitle or "")
    cover_summary = escape(payload.cover_summary or "")
    footer_note = escape(payload.footer_note or "")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>{_premium_report_css()}</style>
</head>
<body>
  <main class="report-shell">
    <section class="cover-block">
      <div class="eyebrow">{escape(payload.branding.product_name)} · Relatorio premium</div>
      <h1>{title}</h1>
      <p class="cover-subtitle">{subtitle}</p>
      <div class="cover-meta">
        <div><span>Academia</span><strong>{gym_name}</strong></div>
        <div><span>Gerado em</span><strong>{generated_label}</strong></div>
        <div><span>Responsavel</span><strong>{generated_by}</strong></div>
        <div><span>Versao</span><strong>{escape(payload.version)}</strong></div>
      </div>
      <p class="cover-summary">{cover_summary}</p>
    </section>
    {sections_html}
    <footer class="report-footer">{footer_note}</footer>
  </main>
</body>
</html>"""


def render_premium_report_pdf(payload: PremiumReportPayload) -> bytes:
    html = render_premium_report_html(payload)
    if payload.report_kind == "body_composition":
        return render_html_to_pdf(
            html,
            viewport={"width": 1120, "height": 1580},
            media="print",
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            scale=1.0,
        )
    return render_html_to_pdf(html)


def render_html_to_pdf(
    html: str,
    *,
    viewport: dict[str, int] | None = None,
    media: str = "screen",
    margin: dict[str, str] | None = None,
    scale: float = 1.0,
) -> bytes:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - exercised in runtime environments
        raise RuntimeError("playwright_unavailable") from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport=viewport or {"width": 1240, "height": 1754})
            page.set_content(html, wait_until="networkidle")
            page.emulate_media(media=media)
            return page.pdf(
                format="A4",
                print_background=True,
                margin=margin or {"top": "18mm", "right": "12mm", "bottom": "18mm", "left": "12mm"},
                scale=scale,
            )
        finally:
            browser.close()


def _render_body_composition_report_html(payload: PremiumReportPayload) -> str:
    report = payload.parameters.get("report") if isinstance(payload.parameters, dict) else None
    if not isinstance(report, dict):
        sections_html = "".join(_render_section(section) for section in payload.sections)
        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <title>{escape(payload.title)}</title>
  <style>{_premium_report_css()}</style>
</head>
<body><main class="report-shell">{sections_html}</main></body>
</html>"""

    header = report.get("header", {}) or {}
    primary_cards = report.get("primary_cards", []) or []
    composition_metrics = report.get("composition_metrics", []) or []
    muscle_fat_metrics = report.get("muscle_fat_metrics", []) or []
    risk_metrics = report.get("risk_metrics", []) or []
    goal_metrics = report.get("goal_metrics", []) or []
    comparison_rows = report.get("comparison_rows", []) or []
    history_series = report.get("history_series", []) or []
    insights = report.get("insights", []) or []
    teacher_notes = report.get("teacher_notes") or "Sem observacoes registradas nesta avaliacao."
    methodological_note = report.get("methodological_note") or payload.footer_note or ""
    data_quality_flags = report.get("data_quality_flags", []) or []
    parsing_confidence = report.get("parsing_confidence")
    technical_scope = payload.report_scope == "technical"
    history_keys = {"weight_kg", "muscle_mass_kg", "body_fat_percent"}
    history_series = [series for series in history_series if str(series.get("key")) in history_keys]
    comparison_priority = {"weight_kg", "body_fat_percent", "muscle_mass_kg", "visceral_fat_level", "bmi"}
    comparison_rows = [row for row in comparison_rows if str(row.get("key")) in comparison_priority]
    comparison_rows = comparison_rows[: (4 if technical_scope else 3)]

    score_metric = _body_metric_by_key(risk_metrics, "health_score") or _body_metric_by_key(primary_cards, "health_score")
    obesity_metrics = [metric for metric in risk_metrics if metric.get("key") in {"bmi", "body_fat_percent"}]
    waist_hip_metric = _body_metric_by_key(risk_metrics, "waist_hip_ratio")
    visceral_metric = _body_metric_by_key(risk_metrics, "visceral_fat_level")
    additional_metrics = [
        metric
        for metric in [
            _body_metric_by_key(composition_metrics, "fat_free_mass_kg"),
            _body_metric_by_key(composition_metrics, "body_water_kg"),
            _body_metric_by_key(composition_metrics, "protein_kg"),
            _body_metric_by_key(primary_cards, "basal_metabolic_rate_kcal"),
            _body_metric_by_key(risk_metrics, "physical_age"),
        ]
        if metric is not None
    ]
    additional_metrics = additional_metrics[: (5 if technical_scope else 4)]
    summary_metrics = [
        metric
        for metric in (
            _body_metric_by_key(primary_cards, "weight_kg"),
            _body_metric_by_key(primary_cards, "body_fat_percent"),
            _body_metric_by_key(primary_cards, "visceral_fat_level"),
            _body_metric_by_key(primary_cards, "muscle_mass_kg"),
            _body_metric_by_key(primary_cards, "bmi"),
            _body_metric_by_key(primary_cards, "basal_metabolic_rate_kcal"),
        )
        if metric is not None
    ]

    generated_label = payload.generated_at.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    measured_label = _format_human_datetime(header.get("measured_at"))
    scope_label = "Relatorio tecnico" if payload.report_scope == "technical" else "Resumo do aluno"
    flags_html = "".join(
        f"<span class=\"clinical-flag\">{escape(_body_flag_label(str(flag)))}</span>"
        for flag in data_quality_flags
    )
    if parsing_confidence is not None:
        flags_html += f"<span class=\"clinical-flag\">OCR {int(round(float(parsing_confidence) * 100))}%</span>"

    lead_insight = insights[0] if insights else None

    teacher_notes = str(teacher_notes).strip()
    if len(teacher_notes) > (140 if technical_scope else 96):
        teacher_notes = teacher_notes[: (137 if technical_scope else 93)].rstrip(" ,;:-") + "..."

    lead_insight_message = str(
        lead_insight.get("message") if lead_insight else "Historico ainda em consolidacao para comparacoes mais fortes."
    ).strip()
    if len(lead_insight_message) > (180 if technical_scope else 110):
        lead_insight_message = lead_insight_message[: (177 if technical_scope else 107)].rstrip(" ,;:-") + "..."

    methodological_note = str(methodological_note or "").strip()
    if len(methodological_note) > (170 if technical_scope else 118):
        methodological_note = methodological_note[: (167 if technical_scope else 115)].rstrip(" ,;:-") + "..."

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <title>{escape(payload.title)}</title>
  <style>{_body_composition_report_css()}</style>
</head>
<body>
  <main class="clinical-shell">
    <section class="clinical-page clinical-sheet {'clinical-sheet-technical' if technical_scope else 'clinical-sheet-summary'}">
      <div class="clinical-sheet-scale">
      <header class="clinical-header">
        <div class="clinical-brand">
          <div class="clinical-brand-name">{escape(payload.branding.product_name)}</div>
          <div class="clinical-brand-line"></div>
          <p>Relatorio premium de composicao corporal estruturado para acompanhamento tecnico e impressao limpa.</p>
        </div>
        <div class="clinical-professional">
          <span class="clinical-kicker">{escape(scope_label)}</span>
          <h1>{escape(str(header.get("member_name") or payload.subject_name or "Aluno"))}</h1>
          <p>{escape(str(header.get("trainer_name") or "Professor nao informado"))}</p>
          <p>{escape(str(payload.branding.gym_name or header.get("gym_name") or "Academia nao informada"))}</p>
          <p class="clinical-generated">Gerado em {escape(generated_label)}</p>
        </div>
      </header>

      <section class="clinical-meta-grid">
        {_render_body_meta_block("ID", str(payload.evaluation_id or payload.entity_id or "-"))}
        {_render_body_meta_block("Altura", _body_header_value(header.get("height_cm"), "cm"))}
        {_render_body_meta_block("Idade", _body_header_value(header.get("age_years"), "anos"))}
        {_render_body_meta_block("Sexo", _body_sex_label(header.get("sex")))}
        {_render_body_meta_block("Data / Hora", measured_label, last=True)}
      </section>

      <section class="clinical-flags">{flags_html}</section>
      <section class="clinical-summary-ribbon">
        {"".join(_render_body_snapshot_compact(metric) for metric in summary_metrics)}
      </section>

      <section class="clinical-main-grid">
        <div class="clinical-left-column">
          <section class="clinical-section">
            <h2>Analise da Composicao Corporal</h2>
            <div class="clinical-table-wrap">
              <table class="clinical-composition-table">
                <tbody>
                  {"".join(_render_body_composition_table_row(metric) for metric in composition_metrics)}
                </tbody>
              </table>
            </div>
          </section>

          <section class="clinical-section">
            <h2>Analise Musculo-Gordura</h2>
            <div class="clinical-band-panel">
              <div class="clinical-band-head">
                <span>Metrica</span>
                <span>Abaixo</span>
                <span>Normal</span>
                <span>Acima</span>
                <span>Valor</span>
              </div>
              {"".join(_render_body_band_row(metric) for metric in muscle_fat_metrics)}
            </div>
          </section>

          <section class="clinical-section">
            <h2>Analise de Obesidade</h2>
            <div class="clinical-band-panel">
              <div class="clinical-band-head">
                <span>Metrica</span>
                <span>Abaixo</span>
                <span>Normal</span>
                <span>Acima</span>
                <span>Valor</span>
              </div>
              {"".join(_render_body_band_row(metric) for metric in [metric for metric in risk_metrics if metric.get("key") in {"bmi", "body_fat_percent"}])}
            </div>
          </section>
        </div>

        <aside class="clinical-right-column">
          <section class="clinical-sidebar-block">
            <h3>Pontuacao corporal</h3>
            <div class="clinical-score">
              <strong>{escape(_body_metric_formatted(score_metric) if score_metric else "--")}</strong>
              <span>/100 Pontos</span>
            </div>
            <p class="clinical-score-copy">Leitura sintetica da composicao corporal para acompanhamento do progresso.</p>
          </section>

          <section class="clinical-sidebar-block">
            <h3>Controle de Peso</h3>
            <div class="clinical-metric-list">{"".join(_render_body_metric_list_row(metric) for metric in goal_metrics)}</div>
          </section>

          <section class="clinical-sidebar-block">
            <h3>Indicadores</h3>
            <div class="clinical-status-list">{"".join(_render_body_status_row(metric) for metric in obesity_metrics)}</div>
            <div class="clinical-mini-gauge-grid">
              {f'<div>{_render_body_mini_gauge(waist_hip_metric)}</div>' if waist_hip_metric else ''}
              {f'<div>{_render_body_mini_gauge(visceral_metric)}</div>' if visceral_metric else ''}
            </div>
          </section>

          {f'''<section class="clinical-sidebar-block">
            <h3>Comparativo rapido</h3>
            <div class="clinical-compact-comparison">
              {"".join(_render_body_compact_comparison_row(row) for row in comparison_rows)}
            </div>
          </section>''' if comparison_rows else ''}

          <section class="clinical-sidebar-block">
            <h3>Dados adicionais</h3>
            <div class="clinical-metric-list">{"".join(_render_body_metric_list_row(metric) for metric in additional_metrics)}</div>
          </section>

          {f'''<section class="clinical-sidebar-block clinical-sidebar-note">
            <h3>Leitura final e observacoes</h3>
            <div class="clinical-note-pair">
              <div>
                <span>Leitura final</span>
                <p>{escape(lead_insight_message)}</p>
              </div>
              <div>
                <span>Observacoes do professor</span>
                <p>{escape(str(teacher_notes or "Sem observacoes registradas nesta avaliacao."))}</p>
              </div>
              {f'<div><span>Nota metodologica</span><p>{escape(str(methodological_note))}</p></div>' if methodological_note else ''}
            </div>
          </section>''' if technical_scope or lead_insight or teacher_notes or methodological_note else ''}
        </aside>
      </section>

      <section class="clinical-section">
        <h2>Historico da Composicao Corporal</h2>
        {_render_body_history_grid(history_series[: (4 if technical_scope else 3)], limit=(5 if technical_scope else 4))}
      </section>
      </div>
    </section>
  </main>
</body>
</html>"""


def _render_section(section: PremiumReportSection) -> str:
    subtitle = f"<p class=\"section-subtitle\">{escape(section.subtitle)}</p>" if section.subtitle else ""
    metrics = _render_metrics(section.metrics)
    narratives = _render_narratives(section.narratives)
    charts = _render_charts(section.charts)
    tables = "".join(_render_table(table) for table in section.tables)
    actions = _render_actions(section.actions)
    return f"""
    <section class="report-section">
      <div class="section-header">
        <h2>{escape(section.title)}</h2>
        {subtitle}
      </div>
      {metrics}
      {narratives}
      {charts}
      {tables}
      {actions}
    </section>
    """


def _render_metrics(metrics: Sequence[PremiumReportMetric]) -> str:
    if not metrics:
        return ""
    cards = "".join(
        f"""
        <article class="metric-card tone-{escape(metric.tone)}">
          <span class="metric-label">{escape(metric.label)}</span>
          <strong class="metric-value">{escape(metric.value)}</strong>
          {f'<span class="metric-hint">{escape(metric.hint)}</span>' if metric.hint else ''}
        </article>
        """
        for metric in metrics
    )
    return f"<div class=\"metric-grid\">{cards}</div>"


def _render_narratives(narratives: Sequence[PremiumReportNarrative]) -> str:
    if not narratives:
        return ""
    blocks = "".join(
        f"""
        <article class="narrative-card tone-{escape(item.tone)}">
          <h3>{escape(item.title)}</h3>
          <p>{escape(item.body)}</p>
        </article>
        """
        for item in narratives
    )
    return f"<div class=\"narrative-grid\">{blocks}</div>"


def _render_table(table: PremiumReportTable) -> str:
    headers = "".join(f"<th>{escape(column)}</th>" for column in table.columns)
    rows = "".join(
        "<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>"
        for row in table.rows
    )
    caption = f"<p class=\"table-caption\">{escape(table.caption)}</p>" if table.caption else ""
    return f"""
    <section class="table-block">
      <div class="block-heading">
        <h3>{escape(table.title)}</h3>
        {caption}
      </div>
      <table>
        <thead><tr>{headers}</tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    """


def _render_charts(charts: Sequence[PremiumReportChart]) -> str:
    if not charts:
        return ""
    return "".join(_render_chart(chart) for chart in charts)


def _render_chart(chart: PremiumReportChart) -> str:
    max_value = max((point.value for point in chart.points), default=0.0)
    max_value = max(max_value, 1.0)
    rows = "".join(
        f"""
        <div class="chart-row">
          <span class="chart-label">{escape(point.label)}</span>
          <div class="chart-bar-track">
            <div class="chart-bar-fill" style="width:{(point.value / max_value) * 100:.1f}%"></div>
          </div>
          <span class="chart-value">{escape(_format_chart_value(point.value, chart.unit))}</span>
        </div>
        """
        for point in chart.points
    )
    insight = f"<p class=\"chart-insight\">{escape(chart.insight)}</p>" if chart.insight else ""
    return f"""
    <section class="chart-block">
      <div class="block-heading">
        <h3>{escape(chart.title)}</h3>
        {insight}
      </div>
      <div class="chart-rows">{rows}</div>
    </section>
    """


def _render_actions(actions: Sequence[PremiumReportAction]) -> str:
    if not actions:
        return ""
    rows = "".join(
        f"""
        <li>
          <strong>{escape(action.title)}</strong>
          {f'<span>{escape(action.detail)}</span>' if action.detail else ''}
        </li>
        """
        for action in actions
    )
    return f"""
    <section class="actions-block">
      <div class="block-heading">
        <h3>Acoes recomendadas</h3>
      </div>
      <ul>{rows}</ul>
    </section>
    """


def _format_chart_value(value: float, unit: str | None) -> str:
    if unit == "R$":
        return _format_currency(value)
    if unit == "%":
        return _format_percent(value)
    if unit == "pts":
        return f"{value:,.1f} pts".replace(",", "X").replace(".", ",").replace("X", ".")
    if unit:
        return f"{value:,.0f} {unit}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _render_body_composition_snapshot_card(metric: dict[str, Any]) -> str:
    delta = _body_metric_delta(metric)
    return f"""
    <article class="clinical-snapshot-card">
      <span>{escape(str(metric.get("label") or "-"))}</span>
      <strong>{escape(str(metric.get("formatted_value") or "-"))}</strong>
      <small>{escape(delta)}</small>
    </article>
    """


def _render_body_composition_table_row(metric: dict[str, Any]) -> str:
    return f"""
    <tr>
      <td>{escape(_body_metric_explanation(str(metric.get("key") or "")))}</td>
      <td>
        <div class="clinical-metric-name">{escape(str(metric.get("label") or "-"))}</div>
        <div class="clinical-metric-unit">{escape(str(metric.get("unit") or ""))}</div>
      </td>
      <td>{escape(_body_metric_formatted(metric))}</td>
      <td>{escape(_body_metric_reference(metric))}</td>
    </tr>
    """


def _render_body_band_row(metric: dict[str, Any]) -> str:
    marker, low_limit, high_limit = _body_metric_band_model(metric)
    return f"""
    <div class="clinical-band-row">
      <div class="clinical-band-name">
        <strong>{escape(_body_metric_label(metric))}</strong>
        <span class="status-{escape(str(metric.get("status") or 'unknown'))}">{escape(_body_metric_status_label(metric))}</span>
      </div>
      <div class="clinical-band-track">
        <div class="clinical-band-segment clinical-band-low" style="width:{low_limit:.1f}%"></div>
        <div class="clinical-band-segment clinical-band-mid" style="left:{low_limit:.1f}%;width:{max(high_limit - low_limit, 8):.1f}%"></div>
        <div class="clinical-band-segment clinical-band-high" style="width:{100 - high_limit:.1f}%"></div>
        <div class="clinical-band-marker" style="left:calc({marker:.1f}% - 1px)"></div>
      </div>
      <div class="clinical-band-value">{escape(_body_metric_formatted(metric))}</div>
    </div>
    """


def _render_body_metric_list_row(metric: dict[str, Any]) -> str:
    return f"""
    <div class="clinical-metric-list-row">
      <span>{escape(_body_metric_label(metric))}</span>
      <strong>{escape(_body_metric_formatted(metric))}</strong>
    </div>
    """


def _render_body_snapshot_compact(metric: dict[str, Any]) -> str:
    delta = _body_metric_delta(metric)
    trend = _body_trend_label(str(metric.get("trend") or "insufficient"))
    return f"""
    <article class="clinical-summary-chip">
      <span>{escape(_body_metric_label(metric))}</span>
      <strong>{escape(_body_metric_formatted(metric))}</strong>
      <small>{escape(delta)} · {escape(trend)}</small>
    </article>
    """


def _render_body_status_row(metric: dict[str, Any]) -> str:
    status = str(metric.get("status") or "unknown")
    return f"""
    <div class="clinical-status-row">
      <span>{escape(_body_metric_label(metric))}</span>
      <strong class="status-{escape(status)}">{escape(_body_metric_status_label(metric))}</strong>
    </div>
    """


def _render_body_compact_comparison_row(row: dict[str, Any]) -> str:
    trend = _body_trend_label(str(row.get("trend") or "insufficient"))
    return f"""
    <div class="clinical-compact-comparison-row">
      <div>
        <strong>{escape(str(row.get("label") or "-"))}</strong>
        <span>{escape(str(row.get("previous_formatted") or "-"))} → {escape(str(row.get("current_formatted") or "-"))}</span>
      </div>
      <div class="clinical-compact-comparison-delta">
        <strong>{escape(_format_body_delta(row))}</strong>
        <span>{escape(trend)}</span>
      </div>
    </div>
    """


def _render_body_mini_gauge(metric: dict[str, Any]) -> str:
    marker, low_limit, high_limit = _body_metric_band_model(metric)
    return f"""
    <div class="clinical-mini-gauge">
      <div class="clinical-mini-gauge-head">
        <strong>{escape(_body_metric_formatted(metric))}</strong>
        <span class="status-{escape(str(metric.get("status") or 'unknown'))}">{escape(_body_metric_status_label(metric))}</span>
      </div>
      <div class="clinical-mini-track">
        <div class="clinical-band-segment clinical-band-low" style="width:{low_limit:.1f}%"></div>
        <div class="clinical-band-segment clinical-band-mid" style="left:{low_limit:.1f}%;width:{max(high_limit - low_limit, 8):.1f}%"></div>
        <div class="clinical-band-segment clinical-band-high" style="width:{100 - high_limit:.1f}%"></div>
        <div class="clinical-band-marker" style="left:calc({marker:.1f}% - 1px)"></div>
      </div>
      <div class="clinical-mini-range">
        <span>{escape(str(metric.get("reference_min") if metric.get("reference_min") is not None else "-"))}</span>
        <span>{escape(str(metric.get("reference_max") if metric.get("reference_max") is not None else "-"))}</span>
      </div>
    </div>
    """


def _render_body_history_grid(history_series: Sequence[dict[str, Any]], *, limit: int = 4) -> str:
    columns = _body_history_columns(history_series, limit=limit)
    if not columns:
        return "<div class=\"clinical-history-empty\">Historico insuficiente para comparacao visual.</div>"

    header = "".join(
        f"<div class=\"clinical-history-date\">{escape(_format_dateish(column))}</div>"
        for column in columns
    )
    rows = "".join(_render_body_history_row(series, columns) for series in history_series)
    return f"""
    <div class="clinical-history-grid" style="grid-template-columns:136px repeat({len(columns)}, minmax(0, 1fr));">
      <div class="clinical-history-head clinical-history-label-head">Metrica</div>
      {header}
      {rows}
    </div>
    """


def _render_body_history_row(series: dict[str, Any], columns: Sequence[str]) -> str:
    points = {str(point.get("evaluation_date")): point for point in series.get("points", []) or []}
    cells = []
    for column in columns:
        point = points.get(column)
        if point and point.get("value") is not None:
            value = _coerce_float(point.get("value"))
            cells.append(
                f"""
                <div class="clinical-history-cell">
                  <span class="clinical-history-dot"></span>
                  <strong>{escape(f"{value:.1f}".replace('.', ','))}</strong>
                </div>
                """
            )
        else:
            cells.append("<div class=\"clinical-history-cell clinical-history-cell-empty\"></div>")
    return f"""
    <div class="clinical-history-row-label">
      <strong>{escape(str(series.get("label") or "-"))}<span>{escape(str(series.get("unit") or "indice"))}</span></strong>
    </div>
    {''.join(cells)}
    """


def _render_body_reasons(reasons: Sequence[Any]) -> str:
    if not reasons:
        return ""
    items = "".join(f"<li>{escape(str(reason))}</li>" for reason in reasons)
    return f"<ul>{items}</ul>"


def _body_metric_by_key(metrics: Sequence[dict[str, Any]], key: str) -> dict[str, Any] | None:
    for metric in metrics:
        if metric.get("key") == key:
            return metric
    return None


def _body_metric_label(metric: dict[str, Any]) -> str:
    return str(metric.get("label") or "-").replace("Ã—", "x").replace("×", "x")


def _body_metric_formatted(metric: dict[str, Any] | None) -> str:
    if not metric:
        return "--"
    return str(metric.get("formatted_value") or metric.get("value") or "--")


def _body_metric_reference(metric: dict[str, Any]) -> str:
    reference_min = metric.get("reference_min")
    reference_max = metric.get("reference_max")
    if reference_min is None and reference_max is None:
        return "(sem faixa)"
    return f"({reference_min if reference_min is not None else '-'} ~ {reference_max if reference_max is not None else '-'})"


def _body_metric_explanation(key: str) -> str:
    explanations = {
        "body_water_kg": "Quantidade total de agua no corpo",
        "protein_kg": "Para a construcao e preservacao muscular",
        "inorganic_salt_kg": "Para fortalecimento estrutural",
        "body_fat_kg": "Reserva energetica atual",
        "fat_free_mass_kg": "Componentes livres de gordura",
        "muscle_mass_kg": "Base muscular do organismo",
    }
    return explanations.get(key, "Leitura corporal")


def _body_metric_status_label(metric: dict[str, Any]) -> str:
    status = str(metric.get("status") or "unknown")
    if status == "adequate":
        return "Normal"
    if status == "low":
        return "Baixo"
    if status == "high":
        return "Acima"
    return "Sem faixa"


def _body_metric_delta(metric: dict[str, Any]) -> str:
    delta_absolute = metric.get("delta_absolute")
    unit = metric.get("unit")
    if delta_absolute is None:
        return "Sem base comparativa"
    try:
        number = float(delta_absolute)
    except (TypeError, ValueError):
        return "Sem base comparativa"
    prefix = "+" if number > 0 else ""
    suffix = f" {unit}" if unit else ""
    return f"{prefix}{number:.1f}".replace(".", ",") + suffix


def _body_metric_band_model(metric: dict[str, Any]) -> tuple[float, float, float]:
    try:
        value = float(metric.get("value"))
        reference_min = float(metric.get("reference_min"))
        reference_max = float(metric.get("reference_max"))
    except (TypeError, ValueError):
        return (50.0, 33.0, 67.0)

    if reference_max <= reference_min:
        return (50.0, 33.0, 67.0)

    span = reference_max - reference_min
    domain_min = max(0.0, reference_min - span * 0.9)
    domain_max = reference_max + span * 0.9
    marker = max(0.0, min(100.0, ((value - domain_min) / (domain_max - domain_min)) * 100))
    low_limit = max(0.0, min(100.0, ((reference_min - domain_min) / (domain_max - domain_min)) * 100))
    high_limit = max(0.0, min(100.0, ((reference_max - domain_min) / (domain_max - domain_min)) * 100))
    return marker, low_limit, high_limit


def _body_history_columns(history_series: Sequence[dict[str, Any]], *, limit: int = 4) -> list[str]:
    dates: list[str] = []
    for series in history_series:
        for point in (series.get("points") or [])[-limit:]:
            evaluation_date = point.get("evaluation_date")
            if evaluation_date and evaluation_date not in dates:
                dates.append(str(evaluation_date))
    return dates[-limit:]


def _body_flag_label(flag: str) -> str:
    labels = {
        "missing_body_fat_percent": "% gordura ausente",
        "missing_muscle_mass": "massa muscular ausente",
        "suspect_bmi": "IMC suspeito",
        "ocr_low_confidence": "OCR com baixa confianca",
        "manually_review_required": "revisao manual",
    }
    return labels.get(flag, flag.replace("_", " "))


def _body_header_value(value: Any, suffix: str) -> str:
    if value in (None, ""):
        return "-"
    return f"{value} {suffix}"


def _body_sex_label(value: Any) -> str:
    if value == "male":
        return "Masculino"
    if value == "female":
        return "Feminino"
    return "-"


def _format_human_datetime(value: Any) -> str:
    if not value:
        return "Sem registro"
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            return value
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    return str(value)


def _format_body_delta(row: dict[str, Any]) -> str:
    delta_absolute = row.get("difference_absolute")
    unit = row.get("unit")
    if delta_absolute is None:
        return "-"
    try:
        number = float(delta_absolute)
    except (TypeError, ValueError):
        return "-"
    prefix = "+" if number > 0 else ""
    suffix = f" {unit}" if unit else ""
    return f"{prefix}{number:.1f}".replace(".", ",") + suffix


def _body_trend_label(trend: str) -> str:
    labels = {
        "up": "Subiu",
        "down": "Desceu",
        "stable": "Estavel",
        "insufficient": "Sem base",
    }
    return labels.get(trend, "Sem base")


def _body_tone(tone: str) -> str:
    if tone in {"positive", "warning", "neutral"}:
        return tone
    return "neutral"


def _render_body_meta_block(label: str, value: str, *, last: bool = False) -> str:
    border = " clinical-meta-last" if last else ""
    return f"""
    <article class="clinical-meta-card{border}">
      <span>{escape(label)}</span>
      <strong>{escape(value)}</strong>
    </article>
    """


def _body_composition_report_css() -> str:
    return """
      :root {
        --paper: #fbfaf7;
        --surface: #ffffff;
        --line: #d8d5d0;
        --line-soft: #ebe6df;
        --text: #171311;
        --muted: #6f665f;
        --brand: #b7422f;
        --band-low: #dad5cf;
        --band-mid: #bcc3cc;
        --ok: #0f8c62;
        --warn: #b7791f;
        --high: #b4233c;
      }
      * { box-sizing: border-box; }
      html, body {
        margin: 0;
        padding: 0;
        background: #ffffff;
        color: var(--text);
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }
      .clinical-shell {
        padding: 0;
      }
      .clinical-page {
        width: 202mm;
        max-width: 202mm;
        height: 297mm;
        margin: 0 auto;
        background: var(--surface);
        border: 1px solid var(--line);
        box-shadow: none;
        padding: 5.5mm 6.5mm 4.5mm;
        page-break-after: avoid;
        break-after: avoid-page;
        overflow: hidden;
      }
      .clinical-sheet-summary { --sheet-scale: 1; }
      .clinical-sheet-technical { --sheet-scale: 1; }
      .clinical-sheet-scale {
        width: 100%;
        max-width: 100%;
      }
      .clinical-sidebar-block,
      .clinical-note-block,
      .clinical-insight {
        break-inside: avoid;
        page-break-inside: avoid;
      }
      .clinical-header {
        display: grid;
        grid-template-columns: 1.08fr 0.92fr;
        gap: 14px;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--brand);
      }
      .clinical-brand-name {
        font-size: 38px;
        font-weight: 900;
        letter-spacing: -0.08em;
        color: var(--brand);
        text-transform: uppercase;
        line-height: 0.95;
      }
      .clinical-brand-line {
        width: 156px;
        height: 3px;
        background: var(--brand);
        margin: 7px 0 8px;
      }
      .clinical-brand p,
      .clinical-professional p,
      .clinical-generated,
      .clinical-score-copy,
      .clinical-footer,
      .clinical-note-block p,
      .clinical-insight p,
      .clinical-insight li {
        color: var(--muted);
      }
      .clinical-brand p,
      .clinical-professional p,
      .clinical-score-copy {
        margin: 4px 0 0;
        font-size: 9px;
        line-height: 1.25;
      }
      .clinical-kicker,
      .clinical-meta-card span,
      .clinical-snapshot-card span,
      .clinical-band-head,
      .clinical-history-head,
      .clinical-history-date {
        font-size: 9px;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        font-weight: 700;
        color: #7b7169;
      }
      .clinical-professional {
        text-align: right;
      }
      .clinical-professional h1 {
        margin: 4px 0;
        font-size: 22px;
        line-height: 1.05;
      }
      .clinical-meta-grid {
        display: grid;
        grid-template-columns: 1.45fr 0.8fr 0.75fr 0.85fr 1.25fr;
        border: 1px solid var(--line);
        background: #f7f5f1;
        margin-top: 8px;
      }
      .clinical-meta-card {
        padding: 6px 8px;
        border-right: 1px solid var(--line);
      }
      .clinical-meta-last { border-right: 0; }
      .clinical-meta-card strong {
        display: block;
        margin-top: 3px;
        font-size: 11px;
        line-height: 1.15;
        word-break: break-word;
      }
      .clinical-flags {
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
        margin-top: 6px;
      }
      .clinical-flag {
        border: 1px solid var(--line);
        background: #f7f5f1;
        color: #564d46;
        padding: 3px 7px;
        font-size: 9px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
      }
      .clinical-summary-ribbon {
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 5px;
        margin-top: 6px;
      }
      .clinical-summary-chip {
        border: 1px solid var(--line);
        background: #fbfaf7;
        padding: 5px 6px;
      }
      .clinical-summary-chip strong {
        display: block;
        margin-top: 3px;
        font-size: 12px;
        line-height: 1;
      }
      .clinical-summary-chip span {
        display: block;
        color: #625952;
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-weight: 700;
      }
      .clinical-summary-chip small {
        display: inline-block;
        margin-top: 3px;
        color: #5e554e;
        font-size: 9px;
        line-height: 1.15;
      }
      .clinical-main-grid {
        display: grid;
        grid-template-columns: 1.66fr 1.06fr;
        gap: 10px;
        margin-top: 8px;
      }
      .clinical-left-column,
      .clinical-right-column {
        display: grid;
        gap: 8px;
      }
      .clinical-section h2 {
        margin: 0 0 5px;
        font-family: Georgia, "Times New Roman", serif;
        font-size: 17px;
        font-weight: 600;
        color: #4f433a;
      }
      .clinical-sidebar-block {
        border-top: 1px solid var(--line);
        padding-top: 5px;
      }
      .clinical-sidebar-block h3,
      .clinical-note-block h3,
      .clinical-insight-title {
        margin: 0;
        font-size: 12px;
        font-weight: 700;
      }
      .clinical-score {
        display: flex;
        align-items: baseline;
        gap: 6px;
        margin-top: 4px;
      }
      .clinical-score strong {
        font-size: 30px;
        line-height: 0.95;
        letter-spacing: -0.05em;
      }
      .clinical-score span {
        font-size: 12px;
        color: #625952;
      }
      .clinical-table-wrap {
        border: 1px solid var(--line);
        background: #fbfaf7;
        overflow: hidden;
      }
      table {
        width: 100%;
        border-collapse: collapse;
      }
      .clinical-composition-table td {
        padding: 4px 5px;
        border-top: 1px solid var(--line-soft);
        vertical-align: top;
        font-size: 9px;
      }
      .clinical-composition-table tr:first-child td { border-top: 0; }
      .clinical-composition-table td:nth-child(1),
      .clinical-composition-table td:nth-child(2),
      .clinical-composition-table td:nth-child(3) {
        border-right: 1px solid var(--line);
      }
      .clinical-composition-table td:nth-child(3) {
        text-align: right;
        font-size: 13px;
        font-weight: 700;
      }
      .clinical-metric-name {
        font-weight: 700;
      }
      .clinical-metric-unit {
        color: #736962;
        font-size: 9px;
        margin-top: 2px;
      }
      .clinical-band-panel {
        border: 1px solid var(--line);
        background: #fbfaf7;
        padding: 5px 6px 6px;
      }
      .clinical-band-head,
      .clinical-band-row {
        display: grid;
        grid-template-columns: 98px 1fr 64px;
        gap: 7px;
        align-items: center;
      }
      .clinical-band-head {
        padding-bottom: 4px;
        border-bottom: 1px solid var(--line);
      }
      .clinical-band-head span:nth-child(2),
      .clinical-band-head span:nth-child(3),
      .clinical-band-head span:nth-child(4) {
        display: none;
      }
      .clinical-band-head span:nth-child(2) {
        grid-column: 2;
        display: block;
        text-align: center;
      }
      .clinical-band-row {
        padding-top: 5px;
      }
      .clinical-band-name strong {
        display: block;
      }
      .clinical-band-name span,
      .clinical-status-row strong,
      .clinical-mini-gauge-head span {
        font-size: 9px;
        font-weight: 700;
      }
      .clinical-band-track,
      .clinical-mini-track {
        position: relative;
        height: 8px;
        border: 1px solid var(--line);
        background: #f1efeb;
        overflow: hidden;
      }
      .clinical-band-segment {
        position: absolute;
        inset-y: 0;
      }
      .clinical-band-low {
        left: 0;
        background: var(--band-low);
      }
      .clinical-band-mid {
        background: var(--band-mid);
      }
      .clinical-band-high {
        right: 0;
        background: var(--band-low);
      }
      .clinical-band-marker {
        position: absolute;
        inset-y: 0;
        width: 2px;
        background: #111111;
      }
      .clinical-band-value {
        text-align: right;
        font-size: 12px;
        font-weight: 700;
      }
      .clinical-metric-list,
      .clinical-status-list {
        display: grid;
        gap: 3px;
      }
      .clinical-metric-list-row,
      .clinical-status-row {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        font-size: 9px;
      }
      .clinical-metric-list-row span,
      .clinical-status-row span {
        color: #5d544d;
        line-height: 1.05;
      }
      .clinical-mini-gauge-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 5px;
        margin-top: 5px;
      }
      .clinical-mini-gauge-head,
      .clinical-mini-range {
        display: flex;
        justify-content: space-between;
        gap: 10px;
      }
      .clinical-mini-gauge-head strong {
        font-size: 14px;
      }
      .clinical-mini-range {
        margin-top: 2px;
        font-size: 8px;
        color: #7a7068;
        text-transform: uppercase;
        letter-spacing: 0.1em;
      }
      .status-adequate { color: var(--ok); }
      .status-low { color: var(--warn); }
      .status-high { color: var(--high); }
      .status-unknown { color: #6f665f; }
      .clinical-history-grid {
        display: grid;
        border: 1px solid var(--line);
        background: #fbfaf7;
      }
      .clinical-history-head,
      .clinical-history-date,
      .clinical-history-row-label,
      .clinical-history-cell {
        border-top: 1px solid var(--line-soft);
        border-right: 1px solid var(--line-soft);
        padding: 2px 4px;
      }
      .clinical-history-head,
      .clinical-history-date {
        border-top: 0;
        background: #f0ece8;
      }
      .clinical-history-label-head {
        border-right: 1px solid var(--line);
      }
      .clinical-history-row-label strong {
        display: flex;
        align-items: baseline;
        gap: 6px;
        font-size: 9px;
      }
      .clinical-history-row-label span {
        color: #786f67;
        font-size: 7px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }
      .clinical-history-cell {
        display: flex;
        flex-direction: row;
        align-items: center;
        justify-content: center;
        gap: 4px;
        min-height: 21px;
      }
      .clinical-history-cell strong {
        font-size: 11px;
        line-height: 1;
      }
      .clinical-history-cell-empty {
        background: repeating-linear-gradient(
          45deg,
          #fbfaf7,
          #fbfaf7 10px,
          #f3f0eb 10px,
          #f3f0eb 20px
        );
      }
      .clinical-history-dot {
        width: 5px;
        height: 5px;
        border-radius: 999px;
        background: #111111;
      }
      .clinical-history-empty {
        border: 1px dashed var(--line);
        padding: 12px;
        color: var(--muted);
        background: #fbfaf7;
        font-size: 11px;
      }
      .clinical-compact-comparison {
        display: grid;
        gap: 3px;
      }
      .clinical-compact-comparison-row {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 6px;
        align-items: start;
        padding-top: 3px;
        border-top: 1px solid var(--line-soft);
      }
      .clinical-compact-comparison-row:first-child {
        padding-top: 0;
        border-top: 0;
      }
      .clinical-compact-comparison-row strong {
        display: block;
        font-size: 8px;
      }
      .clinical-compact-comparison-row span {
        display: block;
        color: #6a6059;
        font-size: 7px;
        line-height: 1.08;
      }
      .clinical-compact-comparison-delta {
        text-align: right;
      }
      .clinical-sidebar-note p {
        margin: 2px 0 0;
        color: var(--muted);
        font-size: 7px;
        line-height: 1.08;
      }
      .clinical-note-pair {
        display: grid;
        gap: 4px;
      }
      .clinical-note-pair span {
        display: block;
        color: #6a6059;
        font-size: 7px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }
      .clinical-comparison-table th,
      .clinical-comparison-table td {
        padding: 6px 8px;
        border-top: 1px solid var(--line-soft);
        text-align: left;
        font-size: 11px;
      }
      .clinical-comparison-table thead th {
        border-top: 0;
        background: #f0ece8;
        font-size: 9px;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: #7a7068;
      }
      .clinical-insight-grid {
        display: grid;
        gap: 8px;
      }
      .clinical-insight {
        border: 1px solid var(--line);
        padding: 8px 10px;
      }
      .clinical-insight p,
      .clinical-note-block p {
        margin: 4px 0 0;
        font-size: 11px;
        line-height: 1.35;
      }
      .clinical-insight ul {
        margin: 6px 0 0;
        padding-left: 14px;
        font-size: 10px;
      }
      .tone-positive { background: #eaf7f1; }
      .tone-warning { background: #fff5e9; }
      .tone-neutral { background: #fbfaf7; }
      .clinical-note-block {
        margin-top: 8px;
        border: 1px solid var(--line);
        background: #f7f5f1;
        padding: 8px 10px;
      }
      .clinical-footer {
        border-top: 1px solid var(--line);
        margin-top: 7px;
        padding-top: 6px;
        font-size: 8px;
        line-height: 1.2;
      }
      @page {
        size: A4;
        margin: 0;
      }
    """


def _premium_report_css() -> str:
    return """
      :root {
        color-scheme: light;
        --ink: #101426;
        --muted: #5d657d;
        --line: #d8def0;
        --panel: #f6f8fc;
        --surface: #ffffff;
        --brand: #4f46e5;
        --brand-soft: #eef0ff;
        --warning: #c97a00;
        --warning-soft: #fff4dd;
        --negative: #be123c;
        --negative-soft: #ffe6ef;
        --positive: #0f8c62;
        --positive-soft: #e8fbf4;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--ink);
        background: #edf1f8;
      }
      .report-shell {
        width: 100%;
        max-width: 980px;
        margin: 0 auto;
        padding: 22px 0 18px;
      }
      .cover-block,
      .report-section,
      .report-footer {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 22px;
        box-shadow: 0 12px 32px rgba(16, 20, 38, 0.06);
      }
      .cover-block {
        padding: 30px 34px;
        margin-bottom: 18px;
      }
      .eyebrow {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        color: var(--brand);
        font-weight: 700;
      }
      h1 {
        margin: 10px 0 8px;
        font-size: 34px;
        line-height: 1.05;
      }
      .cover-subtitle,
      .cover-summary,
      .section-subtitle,
      .table-caption,
      .chart-insight,
      .metric-hint,
      .report-footer {
        color: var(--muted);
      }
      .cover-meta {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin: 20px 0;
      }
      .cover-meta div,
      .metric-card,
      .narrative-card {
        border: 1px solid var(--line);
        background: var(--panel);
        border-radius: 16px;
        padding: 14px 16px;
      }
      .cover-meta span,
      .metric-label {
        display: block;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--muted);
        margin-bottom: 6px;
        font-weight: 700;
      }
      .cover-meta strong,
      .metric-value {
        font-size: 18px;
        line-height: 1.2;
      }
      .report-section {
        padding: 24px 28px;
        margin-bottom: 16px;
      }
      .section-header h2,
      .block-heading h3 {
        margin: 0;
      }
      .metric-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin-top: 18px;
      }
      .narrative-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
        margin-top: 14px;
      }
      .tone-positive { background: var(--positive-soft); }
      .tone-warning { background: var(--warning-soft); }
      .tone-negative { background: var(--negative-soft); }
      .table-block,
      .chart-block,
      .actions-block {
        margin-top: 18px;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
      }
      thead th {
        text-align: left;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--muted);
        padding: 10px 12px;
        border-bottom: 1px solid var(--line);
      }
      tbody td {
        padding: 12px;
        border-bottom: 1px solid #edf1f8;
        vertical-align: top;
      }
      .chart-rows {
        margin-top: 12px;
      }
      .chart-row {
        display: grid;
        grid-template-columns: 120px 1fr 120px;
        gap: 12px;
        align-items: center;
        margin-bottom: 10px;
      }
      .chart-bar-track {
        background: #edf1f8;
        border-radius: 999px;
        overflow: hidden;
        height: 12px;
      }
      .chart-bar-fill {
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #4f46e5 0%, #2dd4bf 100%);
      }
      .actions-block ul {
        list-style: none;
        padding: 0;
        margin: 10px 0 0;
        display: grid;
        gap: 10px;
      }
      .actions-block li {
        display: grid;
        gap: 4px;
        padding: 12px 14px;
        border-radius: 14px;
        border: 1px solid var(--line);
        background: var(--panel);
      }
      .report-footer {
        padding: 14px 18px;
        font-size: 12px;
      }
      @page {
        size: A4;
        margin: 0;
      }
    """
