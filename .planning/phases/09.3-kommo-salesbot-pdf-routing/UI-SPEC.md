# UI Spec

## Settings > Kommo
- Adicionar bloco "Roteamento por dominio".
- Cada dominio deve permitir configurar:
  - pipeline
  - etapa
  - salesbot
  - responsavel
  - campo Kommo para mensagem
  - campo Kommo para PDF
  - tags
- Explicar que os campos devem existir na Kommo e que o Salesbot usa esses campos para enviar a mensagem/documento.

## Bioimpedancia
- Botao principal: `Enviar PDF via Kommo`.
- Fallback secundario: `Preparar na Kommo`.
- Estados:
  - `Enviando via Kommo`
  - `Aguardando resposta`
  - `Falhou na Kommo`
  - `Fallback disponivel`

## Work Queue Futuro
- Mesmo roteador deve ser usado por retencao, onboarding, financeiro, comercial e aluno IA.
