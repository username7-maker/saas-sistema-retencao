# Release Notes

## v3.0.0 - 2026-02-14

### Resumo
Entrega do MVP v3.0 do AI GYM OS com arquitetura modular para backend (FastAPI) e frontend (React + TypeScript), incluindo base de segurança, retenção preditiva, CRM, dashboards, NPS, importador e recursos LGPD.

### Backend
- Reestruturação completa para módulos `routers/`, `services/`, `models/`, `schemas/`, `core/`, `utils/` e `background_jobs/`.
- Modelagem SQLAlchemy 2.0 com entidades principais: usuários, membros, check-ins, risco, leads, tarefas, NPS e auditoria.
- Migração Alembic inicial (`20260214_0001_ai_gym_os_mvp_v3.py`) com base do schema do MVP.
- Autenticação JWT (access + refresh), RBAC por perfil e serviços centrais de segurança.
- Job agendado para regras de retenção/risk score e automações associadas.
- Serviços para CRM, dashboards, NPS, importação e exportação LGPD.

### Frontend
- Migração para React + TypeScript com Vite.
- Estrutura modular em `pages/`, `components/`, `layouts/`, `hooks/`, `contexts/` e `services/`.
- Implementação das telas de login, CRM, tasks e dashboards (executivo, comercial, financeiro, operacional e retenção).
- Componentes de gráficos (Recharts) e proteção de rotas.
- Configuração de Playwright para E2E.

### Qualidade e testes
- Backend: testes de permissões e regras de risco adicionados (`pytest`).
- Frontend: cenários E2E críticos de login, dashboard e CRM.
- Limpeza de arquivos legados JS substituídos por TS.

### Segurança e conformidade
- Base para criptografia de dados sensíveis, trilha de auditoria e endpoints LGPD.
- Ajustes de `.gitignore` para evitar versionamento de cache/artefatos locais.

### Observações da release
- Ambiente local ainda depende de PostgreSQL ativo para executar `alembic upgrade head` sem erro de conexão.
- Integrações externas (Supabase, SendGrid, Claude) requerem variáveis reais para operação completa em produção.
