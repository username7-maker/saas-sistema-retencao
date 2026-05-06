# UI Spec

## Principio

O Perfil Operacional deve responder em ate 10 segundos:

1. Qual e o estado do aluno agora?
2. O que precisa ser feito?
3. Por que essa acao foi recomendada?
4. Quem deve agir?
5. O sistema pode resolver sozinho ou precisa humano?

## Layout

### Topo - Resumo do momento

Mostrar:

- nome do aluno
- status
- plano
- turno preferido
- health/operational status quando disponivel
- risco de evasao
- dias sem check-in
- ultima avaliacao
- consentimento de contato
- pendencia critica se houver

### Bloco - Proxima melhor acao

Mostrar como card principal:

- titulo da acao
- dominio
- prioridade
- responsavel sugerido
- turno
- mensagem sugerida quando aplicavel
- evidencias
- bloqueios de Autopilot
- CTA primario

CTA deve ser honesto:

- `Abrir tarefa`
- `Iniciar contato`
- `Abrir WhatsApp`
- `Agendar reavaliacao`
- `Escalar para gerente`
- `Aguardar resposta`

Nao mostrar "enviar automaticamente" se `auto_send` nao estiver habilitado.

### Bloco - Sinais criticos

Separar sinais por severidade:

- Critico
- Atencao
- Positivo

Exemplos:

- pedido de cancelamento
- cobranca contestada
- 14+ dias sem check-in
- NPS baixo
- avaliacao pendente
- fez check-in hoje
- pagamento confirmado

### Bloco - Esteira operacional

Mostrar:

- tasks abertas
- tasks vencidas
- actions do Autopilot aguardando resposta
- ultimas tentativas
- ultimo outcome

### Timeline 360

Timeline com filtros:

- Tudo
- Operacao
- Treino
- Avaliacao
- Financeiro
- Comunicacao
- Autopilot
- CRM
- Risco

## Estados

- Loading: skeleton por bloco.
- Empty: explicar que nao ha dado real naquela area.
- Error parcial: bloco falhou sem derrubar a tela inteira.
- Sem permissao: mostrar mensagem curta e nao renderizar dado sensivel.

## Responsividade

- Desktop: topo + acao principal em duas colunas.
- Mobile: acao principal vem antes da timeline.

## Guardrails

- Nao expor dado sensivel para cargo sem permissao.
- Nao esconder bloqueios de Autopilot.
- Nao transformar recomendacao em promessa de execucao automatica.
