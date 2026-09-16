# Validacao do scanner inteligente

## Automatizada

- stream que chega depois do fechamento e encerrado;
- troca/invalidation mantem apenas um stream;
- permissao negada oferece tentar novamente e galeria;
- analise encontra o recibo e mede nitidez de topo, centro e rodape;
- desfoque regional e movimento impedem captura automatica;
- contagem exige 1,5 s validos mais tres segundos e cancela ao degradar;
- geometria considera o retangulo real de `object-contain`;
- OpenCV corrige perspectiva automatica e quatro cantos manuais;
- endpoint rejeita tipo, tamanho e imagem sem documento, sem persistencia;
- contratos existentes de OCR e captura segmentada continuam compativeis.

Resultado local em 16/09/2026:

- backend: 1.313 testes aprovados;
- frontend: 250 testes aprovados em 56 arquivos;
- ESLint aprovado;
- TypeScript e build de producao aprovados;
- maior chunk: 466,70 kB, abaixo do limite de 500 kB;
- `python -m compileall` e `git diff --check` aprovados.

## Antes de expandir alem do piloto

## Revisao de captura e confirmacao em 16/09/2026

- Confirmacao usa a versao escolhida (original/corrigida) e fica bloqueada
  durante preparo e ajuste dos cantos; tentativas antigas sao abortadas.
- Mudanca de dispositivos e enumeracao atrasada nao reabrem a camera apos
  captura/fechamento. Reiniciar a captura limpa o processamento da parte anterior.
- Analise ao vivo em Web Worker; contorno inclinado, reflexo localizado,
  orientacao sem documento, zoom e geometria de rotacao revisados.
- Frontend: 268 testes aprovados em 57 arquivos com `--maxWorkers=4`;
  ESLint, TypeScript, build e limite de bundle aprovados.
- Playwright Chromium: camera sintetica, worker real, tracks encerradas,
  recorte apos rotacao e confirmacao da original aprovados.
- Dois testes adicionais reproduziram e validaram a correcao da enumeracao
  atrasada e a confirmacao sequencial de tres partes.
- Backend sem alteracoes nesta revisao. Publicacao via CLI autenticado segue
  o fluxo anterior, pois o workflow remoto nao tem os secrets do Railway.

## Validacao fisica pendente

- smoke fisico em Android/Chrome, iPhone/Safari, webcam USB/Chrome e camera
  integrada;
- conferir coincidencia entre contorno original e folha corrigida;
- confirmar encerramento do indicador fisico da camera ao fechar/trocar/sair;
- validar foto unica, tres partes, galeria, permissao negada e troca de camera;
- observar sete dias antes de decidir a expansao.
