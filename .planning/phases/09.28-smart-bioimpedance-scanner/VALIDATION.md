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

- smoke fisico em Android/Chrome, iPhone/Safari, webcam USB/Chrome e camera
  integrada;
- conferir coincidencia entre contorno original e folha corrigida;
- confirmar encerramento do indicador fisico da camera ao fechar/trocar/sair;
- validar foto unica, tres partes, galeria, permissao negada e troca de camera;
- observar sete dias antes de decidir a expansao.
