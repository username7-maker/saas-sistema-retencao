# Hotfix: importacao de check-ins fail-closed

**Data:** 2026-08-31
**Incidente:** um acesso existente no Actuar nao entrou no Cordex; o preview permitia confirmar arquivos com linhas em erro e o commit salvava apenas as linhas validas.

## Decisao

- Importacao de check-ins passa a ser atomica em relacao a erros de linha: se o preview encontrar qualquer erro, o commit fica bloqueado e nenhum check-in e gravado.
- Duplicidades e linhas explicitamente ignoraveis continuam permitidas, pois nao representam perda silenciosa.
- Previews e tentativas de commit bloqueados registram somente hash do arquivo, numeros das linhas e contagem por motivo. O payload da linha e PII nao entram na auditoria.
- A tela permite baixar um CSV de pendencias com numero da linha e motivo.
- A operacao deve exportar uma janela sobreposta de sete dias; a deduplicacao existente torna o reprocessamento seguro e captura acessos feitos depois do corte anterior.
- Plano/assinatura do membro nao faz parte deste hotfix e nao deve ser alterado.

## Validacao esperada

- Backend: preview com uma linha valida e outra invalida retorna `can_confirm=false`.
- Backend: `POST /imports/checkins` executa preflight e responde `422` sem chamar o importador quando existem erros.
- Auditoria: metadados do erro ficam persistidos sem payload de linha.
- Frontend: CTA de confirmar fica desabilitado e oferece download das pendencias.
- Regressao: arquivo Actuar valido continua importando; duplicados continuam idempotentes.

## Resultado

- Backend focado: `62 passed`.
- Frontend focado: `6 passed`; lint sem erros e build de producao verde.
- Railway API `63327694-114f-4fe0-8f59-387c595acb63`: `SUCCESS`.
- Railway worker `d70c1be0-e89f-4745-af81-c376e52a88a5`: `SUCCESS`.
- Vercel `dpl_GjRz5mbDrm9juD9MuEvtVEyXQSr9`: `Ready` e alias de producao atualizado.
- Smoke real: arquivo propositalmente invalido respondeu `422`, nao gravou check-in e gerou auditoria sem payload de linha.
- Reparo controlado: ultimo acesso da aluna afetada passou de `2026-08-23 10:07` para `2026-08-27 11:43`; risco recalculado de `44/yellow` para `31/green`; plano `LIVRE ANUAL` preservado.

## Extensao: arquivo de acessos enviado como cadastro de alunos

Uma nova importacao, feita pela rota de alunos, usou um export do Actuar com colunas `Cliente`, `Assinatura`,
`Data Entrada` e `Hora Entrada`. Os aliases de cadastro interpretaram `Cliente` como nome e `Assinatura` como plano,
atualizando membros existentes. O hotfix de check-ins nao podia atuar porque a requisicao entrou por `/imports/members`.

Decisoes adicionais:

- O preview de alunos identifica a assinatura `Data Entrada` + `Hora Entrada` + identificador de membro como arquivo de
  acessos/catraca, retorna `can_confirm=false` e orienta o envio em `Importar check-ins`.
- O commit de alunos repete o preview no backend e responde `422` antes de qualquer escrita quando o arquivo esta
  bloqueado. A tentativa e auditada apenas com hash, contagens e motivos, sem payload/PII.
- Uma importacao de cadastro nao pode mais sobrescrever `last_checkin_at` quando o membro ja possui um snapshot
  canonico. A partir desse ponto, somente o fluxo de check-ins avanca esse campo.
- Foi criada uma reconciliacao administrativa, isolada por academia e auditada, que recalcula `last_checkin_at` a
  partir do maior `checkins.checkin_at` e atualiza o risco.
- A reparacao de dados fica limitada a Evelyn Casela, cujo plano correto foi confirmado como `LIVRE ANUAL`. Os demais
  membros nao devem ser corrigidos por inferencia sem um cadastro historico confiavel.
