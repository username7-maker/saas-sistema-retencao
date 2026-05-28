# Spec 039 - Tasks Execution Subfilters

## User Story
Como gestor ou operador do Cordex Gym OS, quero filtrar a fila de tarefas por subcategoria operacional dentro de cada dominio para executar onboarding, retencao e demais rotinas em blocos menores e mais claros.

## Requirements
- O trabalho deve seguir GSD e Spec Kit.
- A tela `/tasks` deve manter os filtros atuais de dominio, estado, turno e busca.
- A fila de execucao deve ganhar um filtro adicional de subcategoria operacional quando o dominio selecionado tiver categorias conhecidas.
- Em `Onboarding`, a V1 deve permitir separar pelo momento da jornada: `Dia 0`, `Dia 1`, `Dia 2-6` e `Dia 7+`.
- Em `Retencao`, a V1 deve permitir separar por estagio/categoria de retencao ja usada pelo sistema: monitoramento, atencao, recuperacao, reativacao, escalar gerente e base fria.
- Em `Professor`, a V1 deve permitir separar por etapa tecnica quando existir: D+8 treino, D+14 feedback e reavaliacao.
- O backend deve expor uma subcategoria operacional canonica em cada item da work queue, sem depender de parsing visual no frontend.
- O filtro deve funcionar para `task` e `ai_triage` quando os dados existirem.
- A V1 nao deve remover nenhum fluxo existente, nem alterar permissao/RBAC.

## Non-Goals
- Criar nova tabela ou migration.
- Refazer a pagina de tarefas inteira.
- Criar filtros analiticos complexos com contagem exata por bucket em todos os estados.
- Mudar a regra de priorizacao da fila.

## Acceptance Criteria
- `specify check` passa antes e depois da implementacao.
- `GET /api/v1/work-queue/items` retorna `execution_bucket` e `execution_bucket_label`.
- A API aceita `bucket=...` e filtra antes da paginacao.
- `/tasks` exibe filtro secundario ao selecionar `Onboarding`, `Retencao` ou `Professor`.
- Ao selecionar `Dia 7+` em onboarding, a chamada da fila usa `bucket=onboarding_d7_plus`.
- Ao selecionar uma categoria de retencao, a chamada da fila usa o bucket correspondente.
- Testes focados de backend e frontend passam.
