# Perfil Operacional Inteligente

## Objetivo

O Perfil Operacional Inteligente transforma o Perfil 360 do aluno em uma central de decisao operacional. Ele nao substitui as abas tecnicas existentes; ele agrega contexto suficiente para responder rapidamente:

- quem e o aluno;
- qual e o risco atual;
- o que ja foi tentado;
- qual e a proxima melhor acao;
- se o Autopilot pode ajudar ou se a acao deve ser humana;
- quais dados podem ou nao ser exibidos por papel.

## Endpoint principal

`GET /api/v1/members/{member_id}/operational-profile`

Retorna:

- `member`: resumo do aluno filtrado por permissao;
- `permissions`: visibilidade aplicada ao papel atual;
- `summary`: leitura rapida de status, risco, tasks e Autopilot;
- `risk`, `activity`, `assessment`: blocos herdados do contexto de inteligencia;
- `financial`: visivel para owner, manager e recepcao;
- `commercial`: visivel para owner, manager e comercial;
- `tasks`: tasks abertas do aluno, com breakdown por dominio;
- `autopilot`: estado atual das acoes automaticas;
- `next_best_action`: acao operacional global;
- `timeline_preview`: eventos recentes de timeline, mensagens, task events, financeiro e Autopilot;
- `notes`: notas estruturadas permitidas para o papel.

## Notas estruturadas

As notas internas deixam de depender apenas de `member.extra_data` e passam a usar `member_notes`.

Endpoints:

- `GET /api/v1/members/{member_id}/notes`
- `POST /api/v1/members/{member_id}/notes`

Tipos iniciais:

- `internal`
- `retention`
- `coach`
- `manager`
- `sales_handoff`
- `health_context`

## Regras de permissao

- Owner/manager: visao completa.
- Recepcao: contato, operacao, financeiro operacional e retencao; sem contexto clinico profundo.
- Professor: treino, avaliacao e contexto tecnico; sem financeiro/comercial sensivel.
- Comercial: origem e contexto comercial; sem saude detalhada.

## Proxima melhor acao

A acao global prioriza, nesta ordem:

1. mensagem sensivel ou pedido de humano;
2. Autopilot aguardando resposta;
3. pendencia financeira visivel ao papel;
4. task aberta/vencida;
5. retencao por inatividade;
6. onboarding em risco;
7. revisao tecnica;
8. manutencao de relacionamento.

## Validacao manual

1. Abrir um aluno ativo com check-in recente e confirmar que a acao nao recomenda retencao desnecessaria.
2. Abrir um aluno 14+ dias sem check-in e confirmar playbook de retencao.
3. Abrir um aluno com pendencia financeira como owner/recepcao e depois como professor; professor nao deve ver valor financeiro.
4. Criar uma nota como professor e confirmar que ela aparece como nota tecnica.
5. Abrir a aba de tarefas do perfil e confirmar que a API filtra por `member_id`.
