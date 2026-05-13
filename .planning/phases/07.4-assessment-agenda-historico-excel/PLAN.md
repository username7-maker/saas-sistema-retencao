# Plano

## Backend

- Criar `AssessmentAppointment` tenant-scoped.
- Criar API `/api/v1/assessment-appointments` para listar, criar e atualizar.
- Criar importacao dedicada em `/api/v1/imports/assessment-appointments/preview` e `/apply`.
- Match de aluno por ID, telefone, email, matricula e nome normalizado.
- Match de professor por nome contra usuarios `trainer`.
- Criar tasks operacionais para falta e pagamento pendente.
- Fazer historico `attended/completed` contar como cobertura historica sem dados tecnicos.

## Frontend

- Adicionar aba `Agenda` na tela de Avaliacoes.
- Adicionar importacao dedicada em Importacoes.
- Mostrar aluno, data/hora, professor, presenca, pagamento e origem.

## Validacao

- Importar planilha real da ProGym em preview.
- Conferir duplicidade.
- Conferir timeline do aluno.
- Conferir fila de avaliacoes.
