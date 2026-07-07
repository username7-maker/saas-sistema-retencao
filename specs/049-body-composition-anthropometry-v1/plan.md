# Plan - Composicao Corporal por Medidas V1

## Ordem de Implementacao

1. Criar campos persistentes em `body_composition_evaluations`.
2. Criar servico de calculo antropometrico com Navy, RFM e GeneOS Composite.
3. Resolver `body_fat_used_percent` no backend antes de gerar IA, relatorio ou sync.
4. Atualizar schemas e relatorio premium para expor contexto de fonte e medidas.
5. Atualizar IA para usar fonte oficial e linguagem de estimativa.
6. Atualizar frontend da Bioimpedancia v2 com Medidas manuais / Antropometria.
7. Atualizar testes focados e validar build.

## Contratos Criticos

- `body_fat_percent` continua aceito em create/update para OCR e compatibilidade.
- `preferred_body_fat_source` controla a fonte desejada.
- Default operacional: `geneos_composite` quando houver medidas suficientes; caso contrario `bioimpedance`.
- `body_fat_used_percent` e sempre resolvido pelo backend.
- Novos campos de perimetria nao entram no payload Actuar V1.

## Riscos

- Regressao em relatorio/PDF se algum bloco continuar filtrando por `body_fat_percent`.
- Quebra de testes OCR se `body_fat_percent` deixar de existir como campo bruto.
- Ambiguidade entre cintura e abdomen em mulheres.
- Uso indevido de medidas de evolucao como entrada de calculo.

## Validacao

- `specify check`
- testes backend focados de body composition e AI
- testes frontend focados de Bioimpedancia e relatorio
- `npm.cmd run lint`
- `npm.cmd run build`
- busca final por usos oficiais indevidos de `body_fat_percent`
