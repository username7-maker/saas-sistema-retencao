# Plano 09.25 - Estabilidade, mobile e scanner de bioimpedancia V2

## Objetivo

Entregar observabilidade sem PII, reduzir trabalho vazio do worker, carregar o
workspace do aluno progressivamente, melhorar os fluxos mobile prioritarios e
tratar o recibo termico de bioimpedancia com pre-processamento transitorio antes
da leitura assistida por IA.

## Escopo implementado

- metricas estruturadas por rota para tempo total, banco e quantidade de SQL;
- sanitizacao do Sentry na API e no worker;
- descoberta previa de academias com filas vencidas e commits somente com trabalho;
- indices compostos das filas de autopilot;
- bootstrap enxuto e opcional do workspace, sem truncar o historico completo;
- scanner com selecao persistida de webcam, resolucao progressiva, capacidades
  reais do dispositivo, estabilidade dos frames e `ImageCapture` com fallback;
- pre-processamento OpenCV em memoria: contorno, perspectiva, orientacao,
  contraste por regioes e compressao adaptativa;
- contrato retrocompativel de captura, qualidade e conflitos com cadastro;
- confirmacao unica e compacta das divergencias do papel;
- cartoes mobile de membros, barra fixa de avaliacao, alvos de 44 px, dialogs com
  `dvh` e safe areas;
- debounce/cancelamento de busca, correcoes de hooks, dependencias e testes;
- orcamento de 500 kB por chunk JavaScript;
- flags `MOBILE_OPERATIONAL_V2`, `BIOIMPEDANCE_SCANNER_V2` e
  `MEMBER_WORKSPACE_BOOTSTRAP_V1`.

## Protecoes

- nenhuma imagem e persistida pelo novo pipeline;
- nenhuma avaliacao historica e recalculada;
- uma escolha pelo valor do papel afeta apenas a avaliacao;
- historico integral e buscado ao abrir Evolucao; o bootstrap guarda somente o
  resumo inicial;
- infraestrutura regional e porta do pooler somente mudam depois de benchmark
  executado dentro da mesma rede de producao.

## Publicacao

1. Validar suites completas, lint, build, migracao e imagem real anonimizada.
2. Confirmar backup logico destacado e versao anterior para rollback.
3. Publicar API e worker pelo mesmo commit.
4. Ativar scanner, mobile e bootstrap na academia piloto.
5. Publicar frontend pelo mesmo commit e executar smoke sem gravar dados.
6. Observar logs de readiness, migracao, worker e erros antes de concluir.

