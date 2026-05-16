# Specification: Cordex Gym OS Branding

## User Story

Como dono do produto, quero que toda marca visivel do sistema use Cordex Gym OS, mantendo compatibilidade tecnica interna e preservando ProGym como academia cliente.

## Functional Requirements

- FR-001: O frontend deve centralizar constantes de marca em `src/config/brand.ts`.
- FR-002: O backend deve centralizar constantes de marca em `app/core/branding.py`.
- FR-003: Login, sidebar, settings, integracoes, relatorios e mensagens visiveis devem usar `Cordex Gym OS`.
- FR-004: E-mails, PDFs e handoffs operacionais devem usar `Cordex Gym OS`.
- FR-005: Chaves tecnicas, cookies, localStorage, migrations, endpoints, schemas e tabelas `ai_gym_*` nao devem ser renomeados.
- FR-006: ProGym deve continuar aparecendo como academia/tenant/parceiro quando aplicavel.

## Acceptance Criteria

- AC-001: Busca em runtime frontend/backend nao encontra `AI Gym OS` em texto visual.
- AC-002: Busca final lista ocorrencias mantidas como legado tecnico, teste legado ou documentacao historica.
- AC-003: Build frontend e testes backend focados passam ou tem bloqueio documentado.

