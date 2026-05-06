# UI Spec - 04.43.10 Regua Tecnica Pos-Avaliacao

## Superficie

Entrada principal: `Tarefas > Modo execucao > Professor`.

## Cards

Cada task tecnica deve mostrar:

- aluno
- turno preferido
- etapa tecnica
- CTA principal
- prazo

## Etapas e CTAs

- `D+8 treino`: CTA `Verificar treino`
- `D+14 feedback`: CTA `Registrar feedback`
- `Reavaliacao`: CTA `Agendar reavaliacao`

## Outcomes rapidos

### D+8

- Treino entregue
- Treino ajustado
- Treino pendente

### D+14

- Feedback positivo
- Precisa ajuste
- Sem resposta

### Reavaliacao

- Reavaliacao agendada
- Sem resposta

## Estados

- Fora da janela: nao aparece em `Fazer agora`.
- Dentro da janela: aparece na fila do professor pelo turno.
- Lista completa: pode localizar tasks futuras.
