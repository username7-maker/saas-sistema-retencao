# Validacao - Phase 09.25

## Local

- Backend completo: `1263 passed`, 12 avisos de depreciacao conhecidos.
- Frontend completo: `219 passed` em 51 arquivos.
- Frontend lint: aprovado sem erros.
- Build TypeScript/Vite: aprovado.
- Bundle: maior chunk 454,91 kB; limite 500 kB aprovado.
- Dependencias de producao: `npm audit --omit=dev` sem vulnerabilidades.
- Alembic: `20260908_0061` e o head unico.
- Imagem real anonimizada de recibo: 899x1599 -> 1000x2874,
  `receipt_perspective+clahe`, confianca de recorte 0,82, sem persistencia.

## Protecoes verificadas

- O parser continua IA-first e OCR local permanece fallback explicito.
- O pre-processamento recebe e devolve bytes somente durante a requisicao.
- `Physical age` nao pode preencher idade cronologica.
- `Value` e `Range` permanecem campos semanticamente separados no prompt.
- Divergencias de idade, sexo e altura usam um unico bloco de confirmacao.
- O cache do bootstrap nao substitui a lista completa de avaliacoes.
- Mobile, scanner e bootstrap permanecem desligaveis individualmente por flag.

## Infraestrutura

- Railway API/worker atuais: `us-west2`.
- Supabase pooler atual: AWS `us-east-2`, porta `6543`.
- A rede local bloqueia conexoes diretas 5432/6543; portanto nenhuma troca de
  pooler ou regiao sera feita sem benchmark equivalente dentro do ambiente.
- Backup logico mais recente esta preservado no volume Railway destacado
  `cordex-secure-backup-20260908-volume`.

## Producao

Preencher depois do rollout: commit, deployments, estado da migracao, readiness,
smoke, flags e observacao inicial de logs.

