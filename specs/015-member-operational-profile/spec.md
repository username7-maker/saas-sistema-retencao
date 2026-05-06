# Spec 015 - Perfil Operacional Inteligente

## User Story

Como recepcao, professor ou gestor, quero abrir o perfil do aluno e entender rapidamente o estado atual, a proxima melhor acao, o responsavel e o que ja foi tentado, para agir sem precisar cruzar varias telas.

## Requisitos Funcionais

- RF1: O sistema deve expor `GET /api/v1/members/{member_id}/operational-profile`.
- RF2: O payload deve ser tenant-scoped por `gym_id`.
- RF3: O payload deve consolidar membro, ciclo de vida, atividade, risco, avaliacao, bioimpedancia, financeiro resumido, comercial/origem, comunicacao, consentimento, tasks, Autopilot, timeline preview, sinais e qualidade de dados.
- RF4: O sistema deve usar `member_intelligence_service` como base canonica, sem criar contexto paralelo incompatível.
- RF5: Tasks do aluno devem ser obtidas via filtro backend por `member_id`, nao por listagem ampla filtrada no frontend.
- RF6: O sistema deve gerar uma `next_best_action` global considerando retencao, onboarding, avaliacao, financeiro, CRM, NPS, tasks abertas e Autopilot.
- RF7: Casos sensiveis, opt-out, cancelamento, reclamacao ou contestacao devem vencer acoes comuns.
- RF8: O perfil deve indicar se o Autopilot pode agir, deve aguardar, esta bloqueado ou precisa humano.
- RF9: A timeline operacional deve incluir eventos de task e Autopilot quando existirem.
- RF10: Notas internas devem migrar para `member_notes`, preservando leitura legada de `extra_data`.
- RF11: O perfil deve ser filtrado por role no backend.

## Requisitos Nao Funcionais

- RNF1: Nenhum dado de outro tenant pode aparecer no perfil.
- RNF2: O endpoint deve evitar N+1 critico.
- RNF3: Falhas parciais devem ser explicitas e nao podem gerar dados inventados.
- RNF4: Nenhuma acao externa automatica nova sera criada nesta fase.
- RNF5: Dados sensiveis devem respeitar LGPD e necessidade operacional por cargo.

## Critérios de Aceite

- CA1: Um perfil de aluno carrega por snapshot unico.
- CA2: O frontend deixa de filtrar todas as tasks localmente para achar tasks do aluno.
- CA3: Um aluno com mensagem sensivel recebe next best action de intervencao humana.
- CA4: Um aluno em retencao critica recebe acao de retencao acima de avaliacao comum.
- CA5: Um aluno com avaliacao recente mostra compromissos tecnicos quando existirem.
- CA6: Trainer nao recebe financeiro/comercial sensivel.
- CA7: Receptionist nao recebe dados clinicos profundos.
- CA8: Owner/manager recebem visao completa.
- CA9: Timeline mostra `TaskEvent` e Autopilot quando houver registros.
- CA10: Testes de tenant isolation cobrem snapshot, timeline e notas.
