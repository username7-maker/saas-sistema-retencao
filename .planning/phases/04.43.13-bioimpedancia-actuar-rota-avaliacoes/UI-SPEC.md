# UI Spec

## Bioimpedancia

- O formulario continua oferecendo o fluxo principal `Salvar e enviar ao Actuar`.
- Quando a integracao Actuar estiver disponivel, exibir tambem `Salvar apenas no sistema`.
- O botao secundario deve salvar os dados, gerar IA/laudo local e criar a regua tecnica, mas nao criar tentativa de sync Actuar.
- Mensagem de sucesso deve deixar claro quando o registro ficou apenas no AI Gym OS.

## Relatorio premium

- O cabecalho do relatorio de bioimpedancia deve exibir o logo ProGym ao lado do texto `AI Gym OS`.
- O logo deve aparecer apenas como marca visual do relatorio, sem substituir a marca do produto.

## Tasks / Work Queue

- Cards de primeira avaliacao devem aparecer como operacao/recepcao, nao na fila do professor.
- Cards tecnicos pos-avaliacao/bioimpedancia devem aparecer na fila do professor com CTA claro:
  - `Verificar treino`
  - `Registrar feedback`
  - `Agendar reavaliacao`
- Badges devem indicar a etapa tecnica e o turno preferido do aluno quando existir.
