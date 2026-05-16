# UI Spec

## Settings > Kommo

- Em cada rota de dominio, adicionar `Modo PDF`:
  - `Nativo obrigatorio`
  - `Nativo preferencial`
  - `Somente link`
- Mostrar campos opcionais:
  - Campo `file_uuid`
  - Campo `nome do arquivo`
  - Campo `nota/anexo`
- Texto de ajuda: "Para PDF nativo, o token precisa ter escopo `files` e o Salesbot precisa usar os campos de arquivo."

## Bioimpedancia

- Botao principal: `Enviar PDF nativo via Kommo`.
- Se falhar, mostrar erro explicavel e manter botoes `Preparar na Kommo` e `Enviar WhatsApp`.
- Quando enviado, indicar `PDF anexado na Kommo` e `Salesbot acionado`.
