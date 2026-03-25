# Controlled Pilot Runbook

## Objetivo

Rodar um piloto controlado com uma academia ou poucas unidades, validando se o sistema sustenta a operacao real com:

- importacao segura
- members e drawers confiaveis
- CRM coerente por papel
- tasks operacionais sem backlog artificial
- retencao acionavel
- assessments com task-lite do trainer

Este runbook existe para tirar o piloto do modo "vamos tentando" e levar para um rollout observavel e reversivel.

## Escopo Do Piloto

### Papais liberados

- `owner`
- `manager`
- `receptionist`
- `trainer`

### Modulos no escopo

- autenticacao e acesso por `gym_slug`
- importacao
- members
- CRM
- tasks
- retencao
- assessments / profile 360
- users

### Fora do escopo do go-live inicial

- Claude
- leitura assistida de bioimpedancia
- Actuar
- novas features de produto
- bulk update dedicado
- busca por telefone/CPF

## Criticos Antes De Abrir O Piloto

1. API sobe com:
   - `ENABLE_SCHEDULER=false`
   - `ENABLE_SCHEDULER_IN_API=false`
2. Worker sobe com:
   - `ENABLE_SCHEDULER=true`
3. `GET /health/ready` responde `200`
4. `pytest`, `npm run test`, `npm run lint` e `npm run build` ja passaram no release do piloto
5. Existe owner inicial criado e login testado
6. Redis e banco estao acessiveis antes de liberar usuarios

## Sequencia Recomendada De Go-Live

### D-2 a D-1

1. Subir ambiente do piloto.
2. Rodar migration.
3. Criar owner e manager.
4. Importar uma planilha pequena de homologacao.
5. Validar:
   - preview -> commit
   - members
   - retencao
   - assessments
   - CRM
   - tasks
   - websocket em duas sessoes

### D0

1. Criar usuarios reais da academia.
2. Treinar `owner` e `manager` por 30 a 45 minutos.
3. Treinar `receptionist` no escopo restrito:
   - members
   - CRM leitura
   - retencao
   - tasks
4. Treinar `trainer` no fluxo:
   - assessments
   - contexto do membro
   - task-lite
5. Comecar com uma base pequena e um horario acompanhado.

### D1 a D5

1. Monitorar logs do worker e da API.
2. Validar requests de recalc manual de risco.
3. Confirmar aniversarios de hoje.
4. Coletar prints e exemplos de telas confusas.
5. Registrar qualquer CTA falso, evento perdido ou job nao processado.

## Teste Operacional Minimo Por Papel

### Owner

1. Fazer login.
2. Importar um arquivo pequeno.
3. Abrir `Members`, `Retention`, `Tasks`, `Users`.
4. Confirmar que os dados importados apareceram corretamente.

### Manager

1. Abrir `CRM`, `Retention`, `Assessments`.
2. Executar um follow-up em lead.
3. Abrir um aluno em risco e conferir a fila operacional.

### Receptionist

1. Procurar aluno em `Members`.
2. Abrir CRM em modo leitura.
3. Resolver uma task operacional.
4. Abrir retencao e confirmar que nao ha CTA fora do papel.

### Trainer

1. Abrir `Assessments`.
2. Entrar no contexto do aluno.
3. Ver a task-lite tecnica.
4. Concluir a acao tecnica sem depender do modulo geral de tasks.

## Sinais Que Precisam Ser Observados Todos Os Dias

- import preview -> commit sem divergencia inesperada
- requests de recalc manual de risco saindo de `queued` para `completed`
- aniversarios de hoje aparecendo corretamente
- recepcao sem CTA de mutacao em CRM
- task-lite do trainer aparecendo e sendo resolvida
- ausencia de erro repetido de websocket/job/lock nos logs

## Sinais De Alerta

Interromper ou pausar o piloto se ocorrer qualquer um destes:

- incidente de tenant
- evento websocket importante nao chegando de forma repetida
- request de recalc ficando preso sem processamento
- permissao errada expondo acao de mutacao para papel indevido
- task tecnica do trainer sumindo ou ficando impossivel de concluir
- importacao criando dados incoerentes ou sem previsao confiavel

## Criterio De Saida Do Piloto

O piloto pode ser considerado estavel quando, por 2 a 4 semanas:

- nao houver incidente critico de tenant
- nao houver job perdido com impacto operacional
- owner e manager operarem o core sem improviso
- recepcao nao encontrar tela/CTA falso
- trainer usar o fluxo tecnico sem depender de workaround fora do sistema

## Rollback Basico

1. Congelar novos usuarios no piloto.
2. Desligar o worker se o problema for job recorrente.
3. Reverter backend para o release anterior.
4. Reverter frontend para o release anterior.
5. Validar `health/ready`, login e members antes de retomar.
