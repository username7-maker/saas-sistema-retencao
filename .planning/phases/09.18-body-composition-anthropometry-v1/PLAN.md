# PLAN - 09.18 Body Composition Anthropometry V1

## Implementacao

1. Persistencia e migration
   - novos campos para antropometria, fonte, metodo, confianca, faixa e revisao.
   - backfill de avaliacoes antigas usando `body_fat_percent` como bioimpedancia bruta.

2. Backend
   - servico de calculo Navy/RFM/GeneOS.
   - resolucao de fonte preferida e flags de qualidade.
   - relatorio, PDF e IA lendo `body_fat_used_percent`.
   - Actuar preservado sem novos campos de perimetria.

3. Frontend
   - secao "Medidas manuais / Antropometria" na Bioimpedancia v2.
   - seletor de fonte preferida.
   - card de gordura estimada com fonte, metodo, faixa, confianca e divergencias.
   - microcopy de abdomen medido na linha do umbigo.

4. Validacao
   - testes focados.
   - busca por uso oficial indevido de `body_fat_percent`.
   - build frontend e testes backend.

## Non-goals

- Sem modulo paralelo.
- Sem copia de Actuar.
- Sem perimetria nova enviada para Actuar.
- Sem diagnostico clinico.
- Sem uso de bracos/coxa/panturrilha/torax/ombro para calcular gordura.
