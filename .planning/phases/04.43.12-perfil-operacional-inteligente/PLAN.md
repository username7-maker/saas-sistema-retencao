# Plano

## Entrega 1 - Snapshot operacional unico

1. Criar `member_operational_profile_service.py`.
2. Criar endpoint `GET /api/v1/members/{member_id}/operational-profile`.
3. Reaproveitar `member_intelligence_service` como base canonica.
4. Agregar no payload:
   - dados basicos do membro
   - permissoes/visibilidade por cargo
   - resumo do momento
   - risco e retencao
   - atividade/check-ins
   - avaliacao e bioimpedancia
   - financeiro resumido
   - comercial/origem do lead
   - comunicacao/consentimento
   - tasks abertas e atrasadas
   - estado do Autopilot
   - sinais criticos
   - preview de timeline
   - flags de qualidade de dados
5. Garantir tenant scope por `gym_id` em todas as consultas.
6. Evitar N+1 critico com consultas agregadas e limites claros.

## Entrega 2 - Tasks por aluno no perfil

1. Trocar no frontend o uso de `listAllTasks({ include_retention: true })` + filtro local por chamada filtrada no backend.
2. Usar `/api/v1/tasks?member_id=...` ou helper dedicado em `memberService`.
3. Ordenar por prioridade operacional, atraso, risco, vencimento e origem.
4. Manter paginacao e `include_archived` apenas quando necessario.

## Entrega 3 - Next Best Action global

1. Criar `member_next_best_action_service.py`.
2. Gerar candidatos de:
   - retencao
   - onboarding
   - avaliacao/treino
   - financeiro
   - CRM/comercial
   - NPS/suporte
   - tasks abertas
   - Autopilot
3. Aplicar prioridade global:
   1. seguranca, cancelamento, opt-out, reclamacao ou mensagem sensivel
   2. financeiro critico ou contestado
   3. retencao critica
   4. task humana vencida
   5. onboarding
   6. avaliacao/treino
   7. comercial
   8. manutencao de relacionamento
4. Retornar:
   - `key`
   - `domain`
   - `title`
   - `reason`
   - `priority`
   - `owner_role`
   - `preferred_shift`
   - `can_autopilot`
   - `autopilot_mode`
   - `suggested_message`
   - `blocked_reasons`
   - `evidence`

## Entrega 4 - Timeline operacional ampliada

1. Evoluir `member_timeline_service` ou criar facade que combine fontes existentes.
2. Incluir, com limite e filtros:
   - check-ins
   - avaliacoes
   - bioimpedancia
   - metas/treino/restricoes
   - tasks
   - `TaskEvent`
   - `MessageLog`
   - `AutopilotEvent`
   - `AutopilotAction`
   - `FinancialEntry`
   - eventos de lead/CRM quando vinculados
   - NPS
3. Criar filtros semanticos:
   - tudo
   - operacao
   - treino
   - avaliacao
   - financeiro
   - comunicacao
   - autopilot
   - CRM
   - risco
4. Nao duplicar dados sensiveis em texto livre sem necessidade.

## Entrega 5 - Notas estruturadas

1. Criar tabela `member_notes`.
2. Campos minimos:
   - `id`
   - `gym_id`
   - `member_id`
   - `author_user_id`
   - `note_type`
   - `body`
   - `visibility`
   - `created_at`
   - `updated_at`
   - `deleted_at`
3. Migrar leitura do Perfil 360 para notas estruturadas.
4. Manter compatibilidade lendo `extra_data.profile360_notes` enquanto houver legado.
5. Nao apagar notas antigas.

## Entrega 6 - UI do Perfil Operacional

1. Atualizar `MemberProfile360Page` para consumir o snapshot operacional.
2. Reorganizar topo da tela em:
   - resumo do momento
   - sinais criticos
   - proxima melhor acao global
   - estado do Autopilot
3. Adicionar botao primario contextual:
   - executar proxima acao
   - abrir tarefa
   - abrir WhatsApp manual
   - iniciar acompanhamento
   - agendar reavaliacao
4. Exibir "por que estou vendo isso?" com evidencias.
5. Manter abas tecnicas existentes, sem quebrar avaliacao/bioimpedancia.

## Entrega 7 - Role-aware profile

1. Criar camada de visibilidade no backend.
2. Regras iniciais:
   - owner/manager: perfil completo.
   - receptionist: contato, risco, tasks, check-in, consentimento, proxima acao; sem detalhes clinicos profundos.
   - trainer: avaliacao, treino, restricoes necessarias, evolucao, tasks tecnicas; sem financeiro/comercial sensivel.
   - salesperson: origem, plano, status comercial e handoff; sem restricoes clinicas e notas internas sensiveis.
3. Criar testes de permissao por role.

## Validacao

1. Perfil carrega com um snapshot unico.
2. Tasks do aluno usam filtro backend por `member_id`.
3. Next best action global prioriza caso sensivel acima de avaliacao comum.
4. Timeline mostra `TaskEvent` e Autopilot quando existem.
5. Trainer nao recebe dados financeiros/comerciais sensiveis.
6. Receptionist nao recebe detalhes clinicos profundos.
7. Owner/manager veem perfil completo.
8. Tenant isolation preservado.
9. Frontend build passa.
10. Smoke no piloto com 3 perfis reais: aluno ativo, aluno em retencao e aluno com avaliacao recente.
