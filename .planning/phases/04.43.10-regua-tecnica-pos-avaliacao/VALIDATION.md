# Validation - 04.43.10 Regua Tecnica Pos-Avaliacao

## Validacao automatizada

- Criacao de specs D+8, D+14 e reavaliacao.
- Criacao de tres tasks tecnicas sem duplicidade no helper.
- Match de professor por escopo de turno.
- Outcome tecnico `training_delivered` conclui task.
- Outcome tecnico `training_missing` mantem task aberta e priorizada.
- Work Queue esconde item futuro em `do_now`.

## Validacao manual recomendada

1. Criar avaliacao para aluno com turno preferido definido.
2. Confirmar tres tasks na lista completa.
3. Confirmar que somente a task dentro da janela aparece em `Fazer agora`.
4. Entrar com usuario professor do turno e validar a fila.
5. Registrar `Treino entregue`, `Feedback positivo` e `Reavaliacao agendada`.
6. Criar nova avaliacao para o mesmo aluno e verificar que futuras tasks abertas da regua anterior foram canceladas.
