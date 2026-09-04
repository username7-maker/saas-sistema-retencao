# Validação - Phase 09.23

## Local

- Backend completo: `1261 passed`, 12 avisos de depreciação conhecidos.
- Backend focado em política/template/WhatsApp: `42 passed`.
- Frontend focado: `6 passed`.
- Build frontend de produção: aprovado.
- Migração Alembic: `20260904_0060` é o head único.
- API importada com os novos contratos registrados.

## Cobertura crítica

- Prompt de comunicação não chama provedor sem ação explícita.
- Ação explícita pode chamar o provedor e registra consumo.
- Fallback conserva integralmente a mensagem pronta.
- Dados diretos de contato/documento são removidos antes do prompt.
- Overrides respeitam academia e papel do usuário.
- WhatsApp bloqueia quando o gate global ou da academia está falso.
- A desconexão não oculta uma instância que o provedor ainda reporte como aberta.
- Jornada, briefing e lembrete só avançam com status `sent`.

## Dívida preexistente observada

A suíte frontend completa ainda contém sete falhas em testes antigos de Automations, Assessments, CRM e Tasks. As falhas observadas são mocks de endpoint fora de sincronia, busca sem normalização de acentos e seletores ambíguos (`Onboarding` duplicado). Os testes do compositor, configurações e painel alterados nesta fase passam, e o build TypeScript/Vite foi aprovado. Essa dívida não foi escondida nem ampliada nesta fase.

## Produção

A preencher após backup, migração, publicação e smoke autenticado.

