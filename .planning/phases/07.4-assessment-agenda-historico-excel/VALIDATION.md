# Validacao

Premissa corrigida: a fonte e uma planilha Excel operacional da academia, nao um export Actuar.

## Cenarios obrigatorios

- Importar planilha com aluno, data, hora, professor, presenca e pagamento.
- Linha com professor cadastrado vincula `evaluator_user_id`.
- Linha com professor desconhecido preserva `evaluator_name_raw`.
- Linha com aluno desconhecido fica em erro.
- Reimportar o mesmo arquivo nao duplica.
- Comparecimento conta como historico operacional de avaliacao.
- Historico importado nao cria `Assessment` tecnico.
- Falta cria task para recepcao remarcar.
- Pagamento pendente cria task operacional.

## Validacao automatizada

- Importacao/preview da agenda Excel coberta em `test_import_service_parsing.py`.
- Dashboard/fila de avaliacoes com cobertura historica cobertos em `test_assessment_queue_service.py`.
- Build frontend validado para a aba `Agenda Excel` e fluxo de importacao.

## Validacao de deploy

- Migration aplicada em producao: `20260512_0042`.
- API e worker Railway publicados com sucesso.
- Frontend Vercel publicado no alias do piloto.
- Smoke publico confirmou frontend `200`, API health `200` e endpoint protegido `401` sem sessao.
