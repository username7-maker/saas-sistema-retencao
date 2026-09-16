# Scanner inteligente da bioimpedancia

## Objetivo

Evoluir a captura do comprovante termico com tecnologia propria, decisao humana
e processamento transitorio. O frontend orienta enquadramento e estabilidade; o
backend usa o OpenCV ja existente para perspectiva, fundo, contraste e qualidade.

## Contratos

- `POST /api/v1/members/{member_id}/body-composition/prepare-image` devolve o
  JPEG corrigido no corpo e metadados em `X-Cordex-Scan-Metadata`.
- A resposta usa `Cache-Control: no-store`; nenhuma imagem ou texto OCR e
  persistido pelo preparo.
- Quatro cantos manuais sao coordenadas normalizadas da fotografia original e
  produzem transformacao de perspectiva real no backend.
- `parse-image` permanece retrocompativel e recebe somente a versao confirmada.
- `VITE_BIOIMPEDANCE_SMART_CAPTURE_V1` controla todo o fluxo novo e nasce
  desligada fora do piloto.

## Rollout

1. Publicar API compativel.
2. Publicar frontend com a flag desligada.
3. Habilitar a flag apenas no piloto.
4. Fazer smoke com dados sinteticos em Android/Chrome, iPhone/Safari, webcam USB
   e camera integrada.
5. Comparar repeticao, falha de OCR e tempo de confirmacao por sete dias.
