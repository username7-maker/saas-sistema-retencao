# Spec 031 - Kommo Salesbot PDF Routing

## User Story
Como operador da academia, quero clicar em um botao no Cordex para enviar uma mensagem ou PDF ao aluno pelo numero oficial conectado na Kommo, sem precisar recriar a mensagem manualmente.

## Requisitos
- O sistema deve suportar envio Kommo em modo `salesbot_outbound`.
- O sistema deve manter `handoff_task` como fallback legado.
- O sistema deve configurar rotas por dominio com pipeline, etapa, Salesbot, responsavel, tags e campos customizados.
- Bioimpedancia deve enviar PDF ao aluno via rota `body_composition`.
- O PDF deve ser exposto por link assinado, temporario e tenant-scoped.
- Eventos devem registrar `channel=kommo`, `delivery_mode=salesbot`, ids Kommo e status.

## Nao Requisitos
- Criar Salesbot automaticamente na Kommo.
- Enviar automaticamente sem clique humano.
- Mudar autenticao, tenants ou tabelas antigas.
