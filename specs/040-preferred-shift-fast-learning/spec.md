# Spec 040 - Preferred Shift Fast Learning

## User Story
Como operador do Cordex Gym OS, quero que o turno preferido do aluno seja aprendido rapidamente pelos primeiros check-ins para que alunos novos aparecam na fila certa sem esperar um historico longo.

## Requirements
- O trabalho deve seguir GSD e Spec Kit.
- A janela de check-ins para inferir turno preferido deve ser menor que 120 dias.
- A V1 deve usar uma janela recente de 30 dias.
- Um unico check-in recente deve definir o turno preferido do aluno.
- Se houver empate entre turnos, o aluno deve ficar sem turno preferido.
- Se houver vencedor unico, mesmo com poucos check-ins, esse turno deve ser o preferido.
- Exemplo esperado: tarde no primeiro dia define `afternoon`; tarde + manha empata e limpa; tarde + manha + tarde define `afternoon`.
- Check-ins novos devem atualizar o turno no momento da criacao/importacao, sem esperar job diario.
- A fila de Tasks deve conseguir mostrar turno inferido para alunos sem turno salvo quando houver sinal recente.

## Non-Goals
- Criar campo de origem manual/automatica do turno.
- Criar tela nova de configuracao.
- Alterar os nomes dos turnos.

## Acceptance Criteria
- `specify check` passa.
- Testes de `preferred_shift_service` cobrem 1 check-in, empate e 2 de 3.
- `sync_preferred_shifts_from_checkins` limpa turno quando existe sinal recente empatado.
- Tasks continua carregando sem migration.
