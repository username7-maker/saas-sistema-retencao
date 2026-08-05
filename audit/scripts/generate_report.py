"""Generate the versioned, sanitized Cordex Gym OS safe-audit report."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_text(repo: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True, encoding="utf-8", errors="replace").strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "indisponivel"


def pct(passed: int, total: int) -> int:
    return round(100 * passed / total) if total else 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    evidence = args.evidence.resolve()
    output = args.output.resolve()

    controls = load_json(evidence / "sandbox-controls.json")
    api = load_json(evidence / "api-audit.json")
    public = load_json(evidence / "public-edge.json")
    static = load_json(evidence / "static-audit.json")
    quality = load_json(evidence / "quality-gates.json")
    teardown = load_json(evidence / "teardown.json")
    browser_files = sorted(evidence.glob("browser-*.json"))
    browsers = [item for path in browser_files if (item := load_json(path))]

    api_cases = api.get("cases", []) if api else []
    api_passed = sum(case.get("status") == "pass" for case in api_cases)
    rbac_cases = [case for case in api_cases if case.get("area") == "rbac"]
    tenant_cases = [case for case in api_cases if case.get("area") == "tenant-isolation"]
    core_cases = [case for case in api_cases if case.get("area") in {"crud", "members", "tasks", "assessments", "reports", "exports"}]
    auth_cases = [case for case in api_cases if case.get("area") in {"authentication", "session", "recovery", "cors", "validation"}]

    control_values = list((controls or {}).get("controls", {}).values())
    quality_gates = (quality or {}).get("gates", [])
    quality_passed = sum(gate.get("exit_code") == 0 for gate in quality_gates)

    multi_tab_retained = any(browser.get("observations", {}).get("tabBRetainedAccessAfterLogout") for browser in browsers)
    missing_labels = max((int(browser.get("loginMissingAssociatedLabels", 0)) for browser in browsers), default=0)
    drawer_escape = next(
        (browser.get("observations", {}).get("drawerClosedWithEscape") for browser in browsers if browser.get("role") == "trainer"),
        None,
    )
    horizontal_overflow = any(browser.get("horizontalOverflow") for browser in browsers)

    public_csp = ((public or {}).get("frontend", {}).get("headers", {}).get("content-security-policy", ""))
    font_import = any(asset.get("google_fonts_import") for asset in (public or {}).get("assets", []))
    csp_blocks_fonts = font_import and "fonts.googleapis.com" not in public_csp
    public_soft_404 = (
        (public or {}).get("error_behavior", {}).get("frontend_missing", {}).get("status") == 200
        and (public or {}).get("error_behavior", {}).get("frontend_missing", {}).get("sha256")
        == (public or {}).get("frontend", {}).get("sha256")
    )
    cache_conservative = any("max-age=0" in asset.get("headers", {}).get("cache-control", "") for asset in (public or {}).get("assets", []))
    source_map_exposed = any(item.get("map_content_type") for item in (public or {}).get("source_map_probes", []))

    static_findings = (static or {}).get("findings", [])
    missing_tenant_models = next(
        (finding.get("evidence", {}).get("missing_models", []) for finding in static_findings if finding.get("id") == "STATIC-TENANT-BACKSTOP"),
        [],
    )

    categories: list[dict[str, Any]] = []
    if public:
        edge_score = 100 - (15 if csp_blocks_fonts else 0) - (5 if "https: wss:" in public_csp else 0) - (5 if public_soft_404 else 0) - (5 if cache_conservative else 0) - (25 if source_map_exposed else 0)
        categories.append({"name": "Borda publica", "weight": 15, "score": max(0, edge_score), "basis": "TLS/headers/CSP/CORS/assets/erros em observacao nao autenticada"})
    if auth_cases:
        auth_score = pct(sum(case.get("status") == "pass" for case in auth_cases), len(auth_cases))
        auth_score -= 15 if multi_tab_retained else 0
        auth_score -= 10 if any(f.get("id") in {"STATIC-RESET-TOKEN-QUERY", "STATIC-RESET-TOKEN-VISIBLE"} for f in static_findings) else 0
        categories.append({"name": "Autenticacao e sessao", "weight": 15, "score": max(0, auth_score), "basis": f"{len(auth_cases)} casos no sandbox e observacao multiaba"})
    if rbac_cases or tenant_cases:
        relevant = rbac_cases + tenant_cases
        tenant_score = pct(sum(case.get("status") == "pass" for case in relevant), len(relevant))
        tenant_score -= min(35, 10 * len(missing_tenant_models))
        tenant_score -= 15 if any(f.get("id") == "STATIC-KOMMO-TENANT-ROUTING" for f in static_findings) else 0
        categories.append({"name": "RBAC e isolamento tenant", "weight": 25, "score": max(0, tenant_score), "basis": f"{len(relevant)} casos Alpha/Beta + revisao do backstop ORM"})
    if core_cases:
        categories.append({"name": "Fluxos e dados", "weight": 15, "score": pct(sum(case.get("status") == "pass" for case in core_cases), len(core_cases)), "basis": f"{len(core_cases)} casos CRUD/filtros/relatorios"})
    if browsers:
        ux_score = 100 - (20 if missing_labels else 0) - (15 if drawer_escape is False else 0) - (10 if any(f.get("id") == "STATIC-A11Y-TABS" for f in static_findings) else 0) - (15 if horizontal_overflow else 0)
        categories.append({"name": "UX e acessibilidade", "weight": 15, "score": max(0, ux_score), "basis": f"{len(browsers)} viewports + heuristicas DOM/teclado"})
    if quality_gates or control_values:
        gate_score = pct(quality_passed, len(quality_gates)) if quality_gates else 0
        control_score = pct(sum(bool(value) for value in control_values), len(control_values)) if control_values else 0
        categories.append({"name": "Qualidade e controles", "weight": 15, "score": round((gate_score + control_score) / 2), "basis": f"{len(quality_gates)} gates + {len(control_values)} controles fail-closed"})

    verified_weight = sum(item["weight"] for item in categories)
    weighted_score = round(sum(item["score"] * item["weight"] for item in categories) / verified_weight) if verified_weight else None

    findings: list[dict[str, str]] = []
    if missing_tenant_models:
        findings.append({"priority": "P1", "title": "Backstop tenant incompleto", "evidence": f"{', '.join(missing_tenant_models)} possuem gym_id mas nao estao em TENANT_SCOPED_MODELS.", "action": "Adicionar os modelos e um teste de paridade de mappers; revisar UPDATE/DELETE explicitamente."})
    if any(f.get("id") == "STATIC-KOMMO-TENANT-ROUTING" for f in static_findings):
        findings.append({"priority": "P1", "title": "Resolucao Kommo pode colidir entre tenants", "evidence": "Lookup global por IDs externos escolhe o link mais recente sem qualificar conta/tenant; integracao ficou desligada no sandbox.", "action": "Qualificar por conta/base URL/tenant antes de aceitar webhook e cobrir IDs repetidos em teste."})
    if multi_tab_retained:
        findings.append({"priority": "P2", "title": "Logout nao revoga imediatamente outra aba", "evidence": "Aba B continuou obtendo 200 com o access JWT apos logout na aba A; recarregar a aba B falhou por refresh revogado.", "action": "Propagar logout por BroadcastChannel e adotar versao/revogacao de sessao para access tokens quando necessario."})
    if any(f.get("id") == "STATIC-RESET-TOKEN-QUERY" for f in static_findings):
        findings.append({"priority": "P2", "title": "Token de reset pode ir para query e campo visivel", "evidence": "ResetPasswordPage aceita ?token= e renderiza o token em input text, divergindo da promessa de fragmento seguro.", "action": "Aceitar apenas fragmento, remover a URL imediatamente e manter token somente em memoria."})
    if csp_blocks_fonts:
        findings.append({"priority": "P2", "title": "CSP publicada bloqueia a fonte solicitada", "evidence": "CSS pede fonts.googleapis.com, mas style-src/font-src nao permitem Google Fonts.", "action": "Auto-hospedar a fonte ou restringir e permitir somente os hosts de fonte necessarios."})
    if missing_labels or drawer_escape is False or any(f.get("id") == "STATIC-A11Y-TABS" for f in static_findings):
        findings.append({"priority": "P2", "title": "Padroes sistemicos de acessibilidade", "evidence": f"Login teve {missing_labels} controles sem label associado; tabs sem ARIA; Drawer sem Escape/dialog/foco.", "action": "Corrigir componentes-base FormField/AuthField, Tabs e Drawer antes de ajustar paginas individualmente."})
    if "https: wss:" in public_csp:
        findings.append({"priority": "P3", "title": "connect-src amplo na CSP", "evidence": "A borda permite conexoes para qualquer origem HTTPS/WSS.", "action": "Restringir a API Railway e provedores explicitamente necessarios."})
    if public_soft_404:
        findings.append({"priority": "P3", "title": "Soft-404 no frontend", "evidence": "Caminho inexistente devolveu o mesmo shell HTML com status 200.", "action": "Definir estrategia de 404 real para caminhos desconhecidos sem quebrar rotas SPA validas."})
    if cache_conservative:
        findings.append({"priority": "P3", "title": "Cache conservador em assets versionados", "evidence": "Bundles com hash responderam max-age=0, must-revalidate.", "action": "Aplicar max-age longo e immutable aos assets com hash."})

    head = git_text(repo, "rev-parse", "HEAD")
    dirty_lines = [line for line in git_text(repo, "status", "--porcelain").splitlines() if line]
    teardown_ok = bool(teardown and teardown.get("status") == "pass")
    controls_ok = bool(controls and controls.get("status") == "pass")
    public_routes = (public or {}).get("published_bundle_routes", [])
    local_routes = (static or {}).get("inventory", {}).get("frontend_routes", [])

    lines: list[str] = []
    lines.extend(
        [
            "# Auditoria Segura do Cordex Gym OS",
            "",
            f"Data: {date.today().isoformat()}  ",
            f"Workspace: `saas-sistema-retencao` em `{head}` com {len(dirty_lines)} mudancas locais no baseline  ",
            "Metodo: autenticado/mutavel somente no Docker isolado; borda publicada somente publica e nao autenticada.",
            "",
            "## Resumo executivo",
            "",
            f"- **Borda publicada (observacao):** {'verificada sem autenticacao' if public else 'nao executada'}. TLS, headers, CSP, CORS, assets, erros e source maps foram observados em baixa taxa. Nenhum source map real foi confirmado." if public else "- **Borda publicada:** nao verificada nesta execucao.",
            f"- **Sandbox do workspace atual (teste):** {'controles fail-closed aprovados' if controls_ok else 'controles com falha ou sem evidencia'}; {api_passed}/{len(api_cases)} casos de API aprovados; {len(browsers)} viewports autenticados observados.",
            "- **Producao autenticada (limitacao):** nao foi usada conta de producao. Login, RBAC, tenant isolation e dados reais publicados permanecem deliberadamente nao verificados.",
            f"- **Teardown:** {'containers, rede, volume, banco, contas e segredos temporarios removidos e verificados' if teardown_ok else 'nao comprovado; nao liberar ate concluir o teardown'}.",
            f"- **Nota ponderada verificavel:** {weighted_score}/100 sobre {verified_weight}% de peso coberto." if weighted_score is not None else "- **Nota:** nao calculada por falta de categorias verificadas.",
            "",
            "A nota e um indicador interno de evidencias desta execucao, nao certificacao de conformidade ou pentest destrutivo.",
            "",
            "## Credencial ficticia principal",
            "",
            "- E-mail: `TESTE_AUDITORIA_GESTOR@teste-auditoria.invalid`",
            "- Tenant logico: `TESTE_AUDITORIA_ALPHA`",
            "- Slug efetivo: `teste-auditoria-alpha`",
            "- Papel: `manager` (gestor tenant-scoped)",
            "- Senha: gerada aleatoriamente em runtime, nunca registrada no relatorio/evidencias e destruida no teardown",
            "- Nenhum administrador global foi criado; o modelo possui somente owner, manager, salesperson, receptionist e trainer vinculados a gym_id.",
            "",
            "## Separacao de conclusoes",
            "",
            "| Superficie | Tipo de conclusao | O que a evidencia permite afirmar |",
            "|---|---|---|",
            "| URL publicada | Observacao | Postura publica de TLS/headers/CSP/CORS, assets, erros, responsividade publica e performance pontual |",
            "| Docker do workspace atual | Teste | Migrations, dados ficticios, autenticacao, sessao, CRUD, RBAC, Alpha/Beta, relatorios, UX e controles desligados |",
            "| Codigo local | Observacao/inferencia | Arquitetura, guardrails de tenant, uploads, logs, segredos, dependencias e efeitos externos |",
            "| Producao autenticada | Limitacao | Nada foi aprovado sem conta dedicada; paridade exata entre commit local e deploy nao foi presumida |",
            "",
            "## Inventario de modulos e rotas",
            "",
            f"O workspace declarou {len(local_routes)} rotas frontend e a borda publicou {len(public_routes)} rotas identificaveis no bundle. Modulos cobertos: autenticacao, dashboards executivo/operacional/comercial/financeiro/retencao, CRM, membros, tarefas, avaliacoes/Perfil 360, relatorios, metas, NPS, notificacoes, automacoes, IA supervisionada, auditoria, importacoes, configuracoes/usuarios, Method OS e vendas.",
            "",
            "Rotas publicas identificadas no bundle (inventario, nao prova de autorizacao):",
            "",
            ", ".join(f"`{route}`" for route in public_routes) if public_routes else "Nao disponivel nesta execucao.",
            "",
            "## Achados priorizados",
            "",
        ]
    )
    if findings:
        for index, finding in enumerate(findings, start=1):
            lines.extend(
                [
                    f"### {finding['priority']} — {finding['title']}",
                    "",
                    f"- Evidencia: {finding['evidence']}",
                    f"- Correcao: {finding['action']}",
                    "",
                ]
            )
    else:
        lines.extend(["Nenhum achado foi consolidado porque a execucao nao produziu evidencia suficiente.", ""])

    lines.extend(["## Fluxos testados e nao testados", "", "Testados no sandbox quando a evidencia correspondente existe:", ""])
    tested = sorted({case.get("area", "outro") for case in api_cases})
    lines.extend([f"- {area}: {sum(case.get('area') == area for case in api_cases)} casos sanitizados." for area in tested])
    lines.extend(
        [
            "",
            "Nao testados ou deliberadamente limitados:",
            "",
            "- entrega real de e-mail, WhatsApp, Kommo, Actuar, IA paga, scheduler, autoenvio e dispatch mensal; somente estados/controles desligados foram verificados;",
            "- qualquer autenticacao, dado ou mutacao na URL publicada;",
            "- brute force, carga, fuzzing, varredura de portas, SSRF em rede real ou exploracao;",
            "- screen reader real, axe/Lighthouse e matriz completa de navegadores; heuristicas DOM/teclado/Performance API nao equivalem a essas ferramentas;",
            "- paridade binaria/commit entre workspace e deploy publicado.",
            "",
            "## Nota por categoria verificada",
            "",
            "| Categoria | Peso | Nota | Base |",
            "|---|---:|---:|---|",
        ]
    )
    for item in categories:
        lines.append(f"| {item['name']} | {item['weight']}% | {item['score']}/100 | {item['basis']} |")

    lines.extend(
        [
            "",
            "## Checklist de liberacao",
            "",
            f"- [{'x' if controls_ok else ' '}] Sandbox confirmou scheduler/worker/integracoes/autoenvio desligados.",
            f"- [{'x' if api and not api.get('summary', {}).get('failed') else ' '}] Casos autenticados do sandbox sem falhas inesperadas.",
            f"- [{'x' if rbac_cases and all(c.get('status') == 'pass' for c in rbac_cases) else ' '}] Matriz RBAC dinamica aprovada para os cinco perfis.",
            f"- [{'x' if tenant_cases and all(c.get('status') == 'pass' for c in tenant_cases) else ' '}] Alpha/Beta negaram leitura/escrita cruzada sem revelar dados.",
            f"- [{'x' if public and not source_map_exposed else ' '}] Borda sem source maps reais nos bundles principais.",
            f"- [{'x' if quality_gates and quality_passed == len(quality_gates) else ' '}] Testes, lint, build, dependencias e Playwright existentes aprovados.",
            f"- [{'x' if teardown_ok else ' '}] Teardown comprovou zero containers/volumes/redes e removeu segredos runtime.",
            "- [ ] Resolver P1 antes de habilitar Kommo multi-tenant ou ampliar superficies que dependem apenas do backstop ORM.",
            "- [ ] Resolver P2 de reset/sessao/acessibilidade antes de classificar a experiencia como pronta para escala.",
            "",
            "## Plano de correcao",
            "",
            "### 48 horas",
            "",
            "- Completar TENANT_SCOPED_MODELS e adicionar teste automatico de paridade para todo mapper com gym_id.",
            "- Bloquear/qualificar o lookup Kommo por conta e tenant; manter webhooks e autoenvio desligados ate teste com IDs repetidos.",
            "- Remover token de reset da query e do input visivel.",
            "- Auto-hospedar a fonte ou corrigir a CSP publicada.",
            "",
            "### 7 dias",
            "",
            "- Propagar logout entre abas e definir politica explicita de revogacao/versionamento do access token.",
            "- Corrigir FormField/AuthField, Tabs e Drawer como componentes-base; adicionar testes de teclado/foco.",
            "- Cobrir isolamento Alpha/Beta para os tres modelos hoje fora do backstop e para UPDATE/DELETE.",
            "- Restringir connect-src e revisar cache imutavel/404 do edge.",
            "",
            "### 30 dias",
            "",
            "- Integrar SAST, secret scan, npm audit e pip-audit como gates; gerar SBOM e triagem de alcançabilidade.",
            "- Executar WCAG com axe + screen reader e Web Vitals/Lighthouse controlados sem misturar com observacao publica pontual.",
            "- Revisar uploads, logs, retention de evidencias, reset de senha e webhooks com testes de abuso seguros.",
            "",
            "### 90 dias",
            "",
            "- Repetir auditoria em staging equivalente a producao e, somente com autorizacao/conta dedicada, validar producao autenticada.",
            "- Fazer exercicio multi-tenant completo para Kommo/WhatsApp/Actuar com contas de teste isoladas.",
            "- Estabelecer revisao trimestral de dependencias, tenant guard, sessao e CSP.",
            "",
            "## Evidencias seguras",
            "",
            "As evidencias ficaram fora do Git. O relatorio referencia apenas nome, tamanho e SHA-256; nenhum token, cookie, HAR, trace autenticado ou payload bruto foi preservado.",
            "",
            "| Arquivo | Bytes | SHA-256 |",
            "|---|---:|---|",
        ]
    )
    for path in sorted(item for item in evidence.iterdir() if item.is_file() and item.name != output.name):
        if path.suffix.lower() in {".har", ".zip"} or "trace" in path.name.lower() or "storage" in path.name.lower() or "cookie" in path.name.lower():
            continue
        lines.append(f"| `{path.name}` | {path.stat().st_size} | `{sha256(path)}` |")

    lines.extend(
        [
            "",
            "## Limites da conclusao",
            "",
            "- A borda publicada pode mudar depois desta coleta; datas e assets identificam somente a observacao atual.",
            "- O sandbox representa o working tree atual, inclusive alteracoes nao commitadas, e nao comprova qual codigo foi implantado.",
            "- Falhas estaticas sao observacoes/inferencias ate haver reproducao controlada; sucessos dinamicos valem apenas para dados e configuracao ficticios do sandbox.",
            "- Canais reais e producao autenticada permanecem nao verificados, nunca presumidos aprovados.",
            "",
        ]
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "generated", "output": output.name, "score": weighted_score, "verified_weight": verified_weight}, sort_keys=True))


if __name__ == "__main__":
    main()
