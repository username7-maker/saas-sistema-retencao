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

- Release da aplicação: `384f58b`.
- API Railway: deployment `55c9addd-2e77-486d-aa17-d75e1923ad83`, `SUCCESS`, health ready `ok`.
- Worker Railway: deployment `f743dddf-0f47-4318-8917-6a783c492c84`, `SUCCESS`, scheduler e Redis saudáveis.
- Frontend Vercel: deployment `dpl_22FvHRKi4MwViT5o7XLGLe19M9pg`, alias de produção atualizado e `READY`.
- Migração `20260904_0060` aplicada no Supabase.
- Backup lógico anterior à rotação preservado em volume Railway destacado: 39.932.746 bytes, SHA-256 `1942d089e842701136992c5e00814f3c50040eede83e3b48531101d027ab2dd2`.
- Senha do banco rotacionada; `DATABASE_URL` da API e do worker atualizadas e conferidas como idênticas sem exposição do valor.
- `WHATSAPP_OUTBOUND_ENABLED=false` confirmado na API e no worker.
- Evolution API: `fetchInstances=0` e nenhuma sessão `open`.
- Configuração de WhatsApp das academias limpa/desativada; uma academia afetada, sem exclusão de logs ou histórico.
- Smoke público: frontend e `/health/ready` respondendo; novas rotas respondem `401` sem autenticação, como esperado.
- Smoke autenticado não executado por ausência de credencial de piloto local; nenhuma mensagem real foi enviada.
