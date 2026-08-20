# Plano

## Objetivo
Melhorar a qualidade percebida das mensagens de retencao e tasks, usando agentes especialistas com `gpt-5.4-mini` quando disponivel e fallback deterministico quando nao houver chave ou quando a IA falhar.

## Implementacao
- Adicionar prompts versionados no `ai_prompt_registry_service`.
- Criar `operational_message_ai_service` para safety, contexto e geracao.
- Integrar em retention intelligence, AI triage, assistente de task e Work Queue.
- Expor metadados de mensagem para frontend.
- Permitir regenerar rascunho em tasks e recomendacoes da Central Cordex.

## Garantias
- Sensivel bloqueia IA.
- VIP bloqueia IA e exige humano.
- Templates antigos continuam funcionando.
- Kommo/WhatsApp usam o mesmo texto preparado, sem autoenvio.
