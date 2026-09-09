# Phase 09.26 - Mobile operacional e scanner V3

## Objetivo

Entregar a evolucao mobile e da captura de bioimpedancia de forma aditiva,
retrocompativel e desligavel no piloto, sem recalcular historicos ou persistir
imagens.

## Entregas desta fase

- Componentes compartilhados para secoes recolhiveis, barra de acao mobile,
  viewport com teclado e listas responsivas.
- Controles essenciais com alvo tactil minimo de 44 px e abas com semantica,
  teclado e centraldo da opcao ativa.
- Formularios de bioimpedancia e antropometria organizados em secoes mobile.
- Relatorio web com modo de leitura mobile separado do layout de impressao,
  compartilhamento nativo e comparacao de perimetria preservada.
- Scanner com negociacao da resolucao real, estabilizacao limitada a dois
  segundos, guia diferente para webcam e celular e encerramento das tracks.
- Captura opcional em topo, centro e rodape, protegida por duas flags.
- Uma chamada de IA para ate tres imagens, com papeis explicitos por segmento.
- Pre-processamento transitorio com deteccao do recibo, perspectiva,
  normalizacao de fundo, CLAHE e qualidade por topo/centro/rodape.
- Recomendacao retrocompativel de aproximar ou fotografar em partes.
- Idempotencia na criacao da bioimpedancia, incluindo indice parcial por
  academia, hash do payload e lock transacional no PostgreSQL.

## Protecoes

- `file` continua sendo o contrato minimo do endpoint existente.
- Maximo de tres imagens, 8 MB por arquivo e 20 MB por requisicao.
- Nenhuma imagem ou texto bruto novo e gravado por esta fase.
- Escolhas do papel valem somente para a avaliacao e nao alteram o cadastro.
- A migracao `20260908_0062` e somente aditiva.
- O arquivo local nao versionado `saas-backend/6` permanece intocado.

## Flags

- `VITE_MOBILE_ASSESSMENT_FLOW_V3`
- `VITE_MOBILE_REPORT_READING_V1`
- `VITE_BIOIMPEDANCE_CAPTURE_GUIDE_V3`
- `VITE_BIOIMPEDANCE_SEGMENTED_CAPTURE_V1`
- `VITE_BODY_COMPOSITION_MULTI_IMAGE_PARSE_V1`
- `BODY_COMPOSITION_MULTI_IMAGE_PARSE_V1`

Captura segmentada exige as duas flags do frontend e a flag correspondente no
backend. A API deve ser publicada antes do frontend.

## Rollout

1. Backup e verificacao do head do banco.
2. Aplicar a migracao aditiva.
3. Publicar API e worker no mesmo SHA.
4. Publicar frontend no mesmo SHA.
5. Ativar primeiro guia, fluxo mobile e relatorio no piloto.
6. Ativar captura multi-imagem somente depois do smoke de imagem unica.
7. Monitorar erros, latencia e correcoes manuais antes de expandir.

