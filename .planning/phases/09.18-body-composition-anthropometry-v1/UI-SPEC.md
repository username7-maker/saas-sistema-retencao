# UI-SPEC - 09.18 Body Composition Anthropometry V1

## Bioimpedancia v2

Adicionar bloco "Medidas manuais / Antropometria" dentro do fluxo atual.

Campos de calculo:

- pescoco
- cintura
- abdomen, com microcopy: "Preferencialmente medido na linha do umbigo."
- quadril

Campos de evolucao/perimetria:

- ombros
- torax
- bracos relaxados e contraidos
- coxas
- panturrilhas

## Card de Resultado

Mostrar:

- Gordura corporal estimada
- Fonte usada no relatorio
- Metodo
- Faixa estimada
- Confianca
- Massa gorda estimada
- Massa livre de gordura estimada
- Diferenca contra bioimpedancia bruta, quando existir

## Previa Operacional

Antes de salvar, o formulario deve mostrar uma previa calculada no cliente com:

- checklist do protocolo por sexo, mostrando campos prontos/pendentes para calculo;
- comparativo bilateral de medidas de evolucao quando pares direito/esquerdo estiverem preenchidos;
- gordura estimada
- status: pronto, incompleto, precisa revisao, usando bioimpedancia ou override
- fonte, metodo, confianca e faixa provavel
- Navy e RFM lado a lado
- massa gorda estimada e massa livre estimada
- campos faltantes
- flags de qualidade
- checkboxes explicitos de revisao manual e revisao antropometrica

## Linguagem

Usar "estimativa", "fonte", "tendencia" e "revisao do professor".

Nao usar "diagnostico", "laudo medico" ou frases absolutas.
