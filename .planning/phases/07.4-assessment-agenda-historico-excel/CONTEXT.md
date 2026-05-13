# 07.4 - Agenda de Avaliacoes e Historico Excel

## Objetivo

Transformar a planilha Excel operacional de avaliacoes da ProGym em agenda e historico dentro do AI Gym OS.

## Decisao principal

A planilha nao contem dados tecnicos de avaliacao. Portanto, ela nao deve criar `Assessment` tecnico estruturado. Ela cria `AssessmentAppointment`, que representa agenda, presenca, pagamento e historico operacional.

## Contexto do sistema atual

- `Assessment` guarda avaliacao tecnica formal.
- `BodyCompositionEvaluation` guarda bioimpedancia.
- A fila de avaliacoes ja considera avaliacao formal e bioimpedancia como cobertura tecnica.
- O importador atual reconhece professor/avaliador, mas a agenda operacional por planilha Excel ainda nao existe.

## Resultado esperado

Recepcao e gestores conseguem importar a planilha, ver agenda por dia/semana, saber quem compareceu, quem faltou, quem pagou, quem ficou pendente e qual professor fez/fezaria a avaliacao.
