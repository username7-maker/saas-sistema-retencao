# 09.3 - Kommo Salesbot PDF Routing

## Problema
O botao atual de Kommo prepara uma task/handoff dentro da Kommo, mas nao envia a mensagem ao numero do aluno. Para a ProGym, o comportamento esperado e de um clique: o Cordex resolve o aluno, prepara a mensagem/PDF e dispara o fluxo pela Kommo no dominio certo.

## Decisao
Kommo passa a ter dois modos:

- `handoff_task`: legado/fallback, cria task e contexto para operador na Kommo.
- `salesbot_outbound`: V1 principal, cria/usa lead do dominio, grava campos/tags e executa Salesbot para enviar pelo canal conectado.

"Abas" na Kommo serao modeladas como pipeline, etapa e tags por dominio. Isto respeita o modelo nativo da Kommo e evita uma abstracao fragil.

## Escopo
- Rotas por dominio: `retention`, `onboarding`, `assessment`, `body_composition`, `finance`, `sales`, `student_ai`, `support`.
- PDF temporario assinado para bioimpedancia.
- Settings para pipeline/stage/salesbot/campos por dominio.
- Botao de bioimpedancia envia PDF via Kommo quando rota esta completa.
- Handoff antigo permanece como fallback explicito.

## Fora do Escopo
- Criar Salesbot dentro da Kommo automaticamente.
- Configurar pipelines remotamente sem permissao.
- Autoenvio fora de Kommo.
- Alterar contratos tecnicos persistentes.
