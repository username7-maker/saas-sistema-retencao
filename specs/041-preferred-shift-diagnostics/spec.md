# Spec 041 - Preferred Shift Diagnostics

## User Story
Como operador do Cordex Gym OS, quero entender por que um aluno aparece como `Sem turno` na fila de Tasks para saber se falta check-in recente, se houve empate entre turnos ou se os dados ainda nao foram importados.

## Requirements
- O trabalho deve seguir GSD e Spec Kit.
- A regra de inferencia da fase 040 nao deve mudar: janela de 30 dias, vencedor unico define turno e empate deixa sem turno.
- A Work Queue deve expor diagnostico de turno para itens com aluno quando o turno preferido estiver indefinido.
- O diagnostico deve diferenciar, no minimo:
  - sem check-in recente/importado nos ultimos 30 dias;
  - empate entre turnos recentes;
  - turno resolvido por check-ins quando houver vencedor unico.
- O frontend de Tasks deve mostrar o motivo apenas quando o item estiver `Sem turno`, sem criar poluicao visual para itens que ja tem turno.
- O texto deve ser operacional e curto, adequado para o card e para o detalhe lateral.
- O contrato deve ser aditivo para nao quebrar clientes existentes.

## Non-Goals
- Criar uma nova tela de auditoria de check-ins.
- Alterar importacao de check-ins.
- Alterar filtros por turno.
- Persistir historico novo em migration.

## Acceptance Criteria
- `specify check` passa antes e depois.
- Backend inclui campos opcionais de diagnostico em `WorkQueueItemOut`.
- Tasks mostra `Sem check-in recente/importado nos ultimos 30 dias` quando nao ha sinal recente.
- Tasks mostra empate com contagens quando ha empate, por exemplo `Empate nos ultimos 30 dias: Manha 1, Tarde 1`.
- Testes backend cobrem diagnostico sem sinal e empate.
- Teste frontend cobre exibicao discreta do motivo de `Sem turno`.
