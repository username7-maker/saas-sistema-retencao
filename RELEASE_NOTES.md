# Release Notes

## v3.0.1 - 2026-02-15

### Resumo
Fechamento de producao do MVP com hardening operacional, melhoria de resiliencia das integracoes e ampliacao da cobertura de testes.

### Melhorias backend
- `CORS_ORIGINS` com parser robusto para formato JSON (`["..."]`) e CSV (`a,b,c`).
- Integracao SendGrid protegida contra excecoes, evitando quebra de jobs por falha de provider.
- Analise Claude mais resiliente com parse de JSON puro, bloco markdown e JSON inline.
- Dispatch NPS agora contabiliza apenas envios efetivamente realizados.
- Job de risco atualizado para reutilizar alerta aberto por membro e reduzir duplicidade de alertas.
- Exportacao LGPD em PDF ampliada com historico completo: check-ins, NPS, tasks, risk alerts e auditoria.

### Qualidade e testes
- Novos testes unitarios backend:
  - `tests/test_config.py` (parsing de CORS).
  - `tests/test_nps_service.py` (envio/log de NPS).
- Novo E2E frontend critico:
  - `tests/e2e/notifications.spec.ts` (listagem e marcar notificacao como lida).
- Suite validada com:
  - Backend: `9 passed`.
  - Frontend E2E: `4 passed`.

## v3.0.0 - 2026-02-14

### Resumo
Entrega do MVP v3.0 do AI GYM OS com arquitetura modular para backend (FastAPI) e frontend (React + TypeScript), incluindo base de seguranca, retencao preditiva, CRM, dashboards, NPS, importador e recursos LGPD.

### Backend
- Reestruturacao completa para modulos `routers/`, `services/`, `models/`, `schemas/`, `core/`, `utils/` e `background_jobs/`.
- Modelagem SQLAlchemy 2.0 com entidades principais: usuarios, membros, check-ins, risco, leads, tarefas, NPS e auditoria.
- Migracao Alembic inicial (`20260214_0001_ai_gym_os_mvp_v3.py`) com base do schema do MVP.
- Autenticacao JWT (access + refresh), RBAC por perfil e servicos centrais de seguranca.
- Job agendado para regras de retencao/risk score e automacoes associadas.
- Servicos para CRM, dashboards, NPS, importacao e exportacao LGPD.

### Frontend
- Migracao para React + TypeScript com Vite.
- Estrutura modular em `pages/`, `components/`, `layouts/`, `hooks/`, `contexts/` e `services/`.
- Implementacao das telas de login, CRM, tasks e dashboards (executivo, comercial, financeiro, operacional e retencao).
- Componentes de graficos (Recharts) e protecao de rotas.
- Configuracao de Playwright para E2E.

### Qualidade e testes
- Backend: testes de permissoes e regras de risco adicionados (`pytest`).
- Frontend: cenarios E2E criticos de login, dashboard e CRM.
- Limpeza de arquivos legados JS substituidos por TS.

### Seguranca e conformidade
- Base para criptografia de dados sensiveis, trilha de auditoria e endpoints LGPD.
- Ajustes de `.gitignore` para evitar versionamento de cache/artefatos locais.

### Observacoes da release
- Ambiente local ainda depende de PostgreSQL ativo para executar `alembic upgrade head` sem erro de conexao.
- Integracoes externas (Supabase, SendGrid, Claude) requerem variaveis reais para operacao completa em producao.
