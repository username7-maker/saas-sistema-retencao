# Validacao - Phase 09.25

## Local

- Backend completo: `1264 passed`, 12 avisos de depreciacao conhecidos.
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

- Commit de aplicacao: `68fec752af407c3e89ccf5451af7cb3a56cbdbcf`.
- API Railway: `b1b2a0b7-2e97-47bb-8da7-b915da89a722`, `SUCCESS`.
- Worker Railway: `642c6a61-3352-4608-8e05-e2f5d3ed18be`, `SUCCESS`.
- Frontend Vercel: `dpl_7jcE2S7ERGiwMPgeNAT5XGU8BrwZ`, `READY`, com alias
  `https://saas-frontend-pearl.vercel.app`.
- API, worker e frontend expõem o mesmo SHA.
- Migração `20260908_0061` aplicada com sucesso antes da troca da API.
- Flags do piloto ativas: scanner V2, mobile operacional V2 e bootstrap V1.
- Smoke público: frontend e readiness HTTP 200; rota protegida retorna 401 sem
  autenticação; nenhuma escrita de cliente foi executada.
- Primeira janela Railway: 4 requisições, zero 5xx, p95 de 251 ms.
- Worker: scheduler e Redis saudáveis, CPU atual inferior a 0,001 vCPU e memória
  em torno de 133 MB na primeira janela.
- A observação inicial detectou bloqueio das consultas globais de descoberta das
  filas pelo tenant guard. O prefixo mínimo `autopilot.jobs.` foi incluído na
  allowlist, coberto por teste e reenviado antes do encerramento do rollout.
- Smoke autenticado automatizado não executado porque o repositório não possui
  as credenciais `PILOT_*`; nenhuma credencial foi criada ou persistida para isso.
- `/health/ready` está publicado e validado. O healthcheck nativo do serviço ainda
  precisa ser configurado no painel Railway; a CLI atual não aplicou a alteração
  isolada porque API e worker compartilham o mesmo arquivo de deploy.
- Região/pooler não foram alterados: a decisão permanece bloqueada até benchmark
  dentro da rede de produção, evitando uma troca baseada em suposição.
