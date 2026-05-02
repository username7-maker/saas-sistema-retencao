# UI Spec - 04.43.7 Operacao 24h

## Superficies

- `Users`: campo Turno operacional inclui `Madrugada`.
- `Members`: filtro e cadastro/edicao incluem `Madrugada`.
- `Tasks`: Modo execucao usa `Meu turno`; lista completa tem filtro `Madrugada`; managers veem saneamento da fila.
- `Work Queue`: `my_shift` respeita usuario madrugada.
- `Retention` e `Assessments`: filtros incluem `Madrugada`.
- `CRM`: captura de turno preferido aceita madrugada.

## Saneamento da fila

Bloco visivel apenas para owner/manager:

- Preview de quantas tasks serao arquivadas.
- Breakdown por origem.
- Texto claro: historico preservado; item sai da fila diaria.
- CTA: `Arquivar ruido operacional`.

## Linguagem

- Evitar termos tecnicos como `overnight`.
- Usar `Madrugada` para operador.
- Explicar que arquivar nao conclui, cancela ou apaga.
