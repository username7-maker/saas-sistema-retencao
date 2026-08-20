# Spec 049 - Composicao Corporal por Medidas V1

## Objetivo

Evoluir a Bioimpedancia v2 do Cordex Gym OS para permitir que o professor registre medidas manuais/perimetria e que o sistema calcule uma estimativa de gordura corporal por antropometria. O fluxo existente de bioimpedancia, OCR, relatorio premium, IA, WhatsApp, Kommo e sync Actuar deve continuar funcionando.

## Resultado Esperado

- A avaliacao continua aceitando dados da bioimpedancia normalmente.
- `body_fat_percent` permanece como campo legado/bruto de compatibilidade.
- `body_fat_used_percent` passa a ser o unico percentual oficial para cards principais, relatorio web, PDF, IA, WhatsApp e Kommo.
- O relatorio mostra claramente a fonte usada: bioimpedancia, antropometria/GeneOS ou override manual.
- O formulario mostra uma previa operacional antes de salvar, com valor estimado, fonte, metodo, confianca, faixa, massa gorda/livre estimada, divergencia contra bioimpedancia e flags.
- O relatorio web mostra um painel de fonte oficial da gordura corporal, separando valor usado, bioimpedancia bruta e estimativa antropometrica.
- O percentual calculado por medidas e apresentado como estimativa, nunca diagnostico clinico.

## Non-goals V1

- Nao copiar formula, layout ou logica proprietaria do Actuar.
- Nao criar modulo paralelo de avaliacao fisica.
- Nao recalcular avaliacoes antigas sem medidas manuais.
- Nao enviar novos campos de perimetria para Actuar nesta V1.
- Nao usar braco, coxa, panturrilha, torax ou ombro como entrada direta no calculo de gordura corporal.
- Nao substituir massa muscular da bioimpedancia por estimativa antropometrica.
- Nao apresentar percentual de gordura como diagnostico clinico.

## Regras de Fonte Oficial

- `body_fat_percent`: legado/bruto/compatibilidade/OCR/Actuar.
- `body_fat_bioimpedance_percent`: percentual bruto vindo da bioimpedancia.
- `body_fat_anthropometric_percent`: percentual calculado por medidas.
- `body_fat_used_percent`: percentual oficial usado em produto.
- `body_fat_percent` so pode aparecer em UI/relatorio quando explicitamente rotulado como "gordura corporal bruta da bioimpedancia".

## Medidas de Calculo vs Evolucao

Medidas usadas para calculo de gordura:

- sexo
- altura
- peso
- pescoco
- cintura ou abdomen
- quadril quando aplicavel

Medidas usadas para evolucao/perimetria:

- ombros
- torax
- bracos
- coxas
- panturrilhas
- demais medidas de acompanhamento

## Regras de Calculo

- Homens: Navy usa `abdomen_cm` como fonte primaria; se ausente, usa `waist_cm`.
- Mulheres: Navy usa `waist_cm + hip_cm + neck_cm`; nao substituir `waist_cm` por `abdomen_cm` automaticamente sem flag/alerta.
- `abdomen_cm` deve ter microcopy no frontend: preferencialmente medido na linha do umbigo.
- RFM e usado como conferencia.
- GeneOS Composite compara Navy e RFM.
- Se GeneOS retornar inconsistente, nao trocar `body_fat_used_percent` para antropometria sem revisao manual ou override explicito.

## Qualidade e Revisao

Flags obrigatorias:

- `anthropometry_incomplete`
- `body_fat_source_divergence`
- `anthropometry_needs_review`
- `anthropometry_inconsistent`
- `impossible_measurement_value`
- `abnormal_measurement_variation`

Campos de revisao:

- `body_fat_manual_review_required`
- `body_fat_manual_review_completed`
- `anthropometry_review_completed`

## Configuracao de Fonte Preferida

- `preferred_body_fat_source` define a fonte desejada para o percentual oficial.
- Valores aceitos: `bioimpedance`, `anthropometry`, `geneos_composite`, `manual_override`.
- Default do fluxo: `geneos_composite` quando houver medidas suficientes.
- Se `geneos_composite` ficar inconsistente, a fonte oficial permanece em bioimpedancia bruta ate revisao manual concluida ou override explicito.

## Aceite

- Nenhum componente principal usa `body_fat_percent` como valor oficial.
- OCR continua salvando o percentual bruto.
- Actuar continua recebendo somente campos compativeis existentes.
- PDF, relatorio web, IA, WhatsApp e Kommo usam `body_fat_used_percent`.
- Dados antigos recebem fallback seguro para `body_fat_used_percent = body_fat_percent` e fonte `bioimpedance`.
- Divergencias relevantes entre bioimpedancia e medidas geram alerta.
- Massa muscular da bioimpedancia continua preservada como fonte propria.
- O professor consegue revisar fonte e consistencia antes de salvar, sem esperar o PDF.
