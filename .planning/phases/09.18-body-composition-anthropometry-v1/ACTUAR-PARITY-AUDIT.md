# ACTUAR PARITY AUDIT - 09.18 Body Composition Anthropometry V1

## Escopo

Auditoria de paridade para a V1 de composicao corporal por medidas no fluxo existente de Bioimpedancia v2.

Referencia operacional usada: a academia quer registrar perimetria/medidas como apoio ao percentual de gordura do relatorio, sem copiar layout, formula ou logica proprietaria do Actuar.

## Resultado

Status: paridade funcional V1 atingida para captura, calculo, fonte oficial, relatorio e governanca.

Ainda nao declarar paridade visual total com Actuar em toda a experiencia de avaliacao fisica, porque a V1 fica dentro da Bioimpedancia v2 e nao cria um modulo completo separado de avaliacao fisica.

## Matriz de Paridade

| Area | Actuar esperado pelo processo | Cordex V1 | Status |
| --- | --- | --- | --- |
| Captura de medidas | Professor registra medidas corporais manuais | Bioimpedancia v2 possui secao "Medidas manuais / Antropometria" e "Perimetria para evolucao" | Igual V1 |
| Guia de preenchimento | Professor precisa saber quais medidas importam | Checklist do protocolo por sexo mostra campos prontos/pendentes antes de salvar | Superior em operacao |
| Separacao calculo/evolucao | Medidas principais entram no calculo; demais acompanham evolucao | Calculo usa sexo, altura, peso, pescoco, cintura/abdomen e quadril quando aplicavel; braco/coxa/panturrilha/torax/ombro ficam so para evolucao | Superior em governanca |
| Assimetria operacional | Actuar registra pares de perimetria | Cordex compara pares direito/esquerdo no formulario e destaca delta, sem usar no calculo de gordura | Superior em acao imediata |
| Fonte de gordura corporal | Processo operacional pode preferir medida manual | `body_fat_used_percent` e fonte oficial; `body_fat_percent` e bruto/legado | Superior em rastreabilidade |
| Bioimpedancia preservada | Exame continua com dados brutos | Peso, agua, musculo, visceral, TMB e gordura bruta continuam salvos | Igual V1 |
| Formula proprietaria | Nao copiar | Cordex usa Navy/RFM publicos e GeneOS composite configuravel | Conforme |
| Revisao manual | Professor precisa revisar divergencias | GeneOS inconsistente e divergencia relevante geram flags e review gate | Superior em seguranca |
| Relatorio | Relatorio mostra composicao e medidas | Relatorio web/PDF mostram fonte oficial, bioimpedancia bruta, antropometria, faixa, confianca e tabela de medidas | Superior em transparencia |
| IA | Interpretacao deve entender fonte e tendencia | Payload inclui contexto de fonte, metodo, faixa, divergencia e flags; snapshot pessoal remove campo legado ambiguo | Superior em seguranca |
| WhatsApp/Kommo | Envio deve usar o relatorio correto | PDF/relatorio e payloads principais usam `body_fat_used_percent`; Actuar continua contrato legado sem perimetria nova | Igual V1 |
| Actuar sync | Nao enviar campos novos nesta V1 | Mapeamento Actuar mantem gordura bruta/legada e nao envia perimetria nova | Conforme |

## Evidencia Funcional

- Spec 049 inclui non-goals, fonte oficial, medidas de calculo vs evolucao, regra cintura/abdomen, revisao manual, fonte preferida e flags de qualidade.
- Backend possui servico dedicado `body_composition_anthropometry_service.py`.
- Frontend possui preview local antes de salvar em `bodyCompositionAnthropometryPreview.ts`.
- Relatorio possui painel "Fonte oficial da gordura corporal" e tabela "Medidas corporais".
- Formulario possui checklist do protocolo e comparativo bilateral antes de salvar.
- PDF recebe as mesmas estruturas do report builder.
- Testes focados cobrem calculo masculino/feminino, GeneOS inconsistente, manual override, preview e relatorio.

## Limites V1

- Nao ha copia visual do Actuar.
- Nao ha modulo paralelo de avaliacao fisica.
- Nao ha recalculo retroativo sem medidas.
- Nao ha envio de perimetria nova ao Actuar.
- Nao ha diagnostico clinico.

## Proximos Ajustes Recomendados

1. Criar modo de captura guiada por protocolo, com checklist lateral de medidas obrigatorias por sexo.
2. Mostrar assimetria direita/esquerda para bracos, coxas e panturrilhas.
3. Adicionar grafico de evolucao por medida corporal no historico.
4. Adicionar UAT com professor usando uma avaliacao real completa.
5. Depois da UAT, decidir se a avaliacao fisica completa merece modulo proprio ou continua acoplada a Bioimpedancia v2.
