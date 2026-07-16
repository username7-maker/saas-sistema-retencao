# Spec 056 - Avaliacao antropometrica local sem bioimpedancia

## Summary

Implementar o modo local de avaliacao antropometrica sem depender da balanca de bioimpedancia, dentro do fluxo existente de Nova Avaliacao.

Esta spec cobre somente a V1 local. A integracao com Actuar, IA, WhatsApp, Kommo, revisoes, overrides e modos hibridos ficam fora deste corte.

## Goals

- Permitir que o professor conclua uma avaliacao sem arquivo, OCR, camera ou dado de bioimpedancia.
- Calcular no backend IMC, percentual de gordura, massa de gordura, massa livre de gordura, RCQ e TMB estimada quando aplicavel.
- Persistir snapshot auditavel com protocolo, versao, entradas, tentativas, politica de repeticao, resultados, origem por indicador e hash de calculo.
- Mostrar historico unificado por leitura, sem migrar fisicamente avaliacoes antigas nem recalcular registros historicos.
- Gerar PDF premium identificado como `Avaliacao antropometrica`, omitindo cards sem dado.
- Criar regua D+8, D+14, D+75 e D+90 na confirmacao.
- Manter o fluxo de bioimpedancia congelado.

## Non-goals

- Nao alterar `MemberBodyCompositionTab`, OCR, camera, endpoints, mapper, calculos ou automacoes de bioimpedancia.
- Nao enviar dados ao Actuar.
- Nao enviar dados para IA, WhatsApp ou Kommo.
- Nao implementar edicao, rascunho persistido, revisao, supersessao ou locking otimista.
- Nao estimar massa muscular.
- Nao normalizar tentativas em tabelas proprias.

## Functional contract

### Modo de entrada

Na tela Nova Avaliacao:

- `Com bioimpedancia`: abre o fluxo legado de bioimpedancia.
- `Sem bioimpedancia`: abre o formulario antropometrico guiado.

### Dados informados

- data da avaliacao;
- peso;
- altura;
- sexo usado pela formula;
- idade calculada a partir da data de nascimento;
- protocolo;
- dobras e perimetros exigidos pelo protocolo;
- perimetros opcionais para acompanhamento;
- observacoes.

### Calculos oficiais

O backend e a unica fonte oficial. Preview e confirmacao devem produzir o mesmo resultado e o mesmo hash quando a entrada for igual.

Indicadores calculados:

- IMC;
- percentual de gordura;
- massa de gordura;
- massa livre de gordura;
- relacao cintura-quadril, quando cintura e quadril estiverem presentes;
- TMB estimada por Mifflin-St Jeor para adultos de 19 a 78 anos.

Indicadores indisponiveis na V1:

- massa muscular;
- agua corporal;
- gordura visceral;
- massa ossea;
- idade metabolica/fisica;
- gasto energetico total sem fator de atividade;
- peso-alvo sem meta definida.

Massa livre de gordura nunca deve ser rotulada como massa muscular.

## Data model

O agregado evoluido e `Assessment`. `BodyCompositionEvaluation` permanece congelado.

Campos novos principais:

- `assessment_method`;
- `record_origin`;
- `sex_used_for_formula`;
- `age_used_for_formula`;
- `height_used_for_formula`;
- `weight_used_for_formula`;
- `measurement_protocol`;
- `formula_version`;
- `calculation_hash`;
- `idempotency_key`;
- `anthropometry_snapshot_json`.

Valores de V1:

- `assessment_method=manual_anthropometry`;
- `record_origin=cordex`.

Registros antigos recebem apenas `record_origin=legacy` no backfill. `assessment_method` fica nulo quando o metodo historico nao puder ser determinado com seguranca.

## Measurement policy

`measurement_policy_version=anthropometry-v1`.

- dobras e perimetros sao medidos no lado direito;
- excecoes de lado exigem motivo registrado;
- medidas usadas em formula exigem duas tentativas;
- diferenca de dobras acima de 5% exige terceira tentativa;
- diferenca de altura ou perimetros acima de 1% exige terceira tentativa;
- duas tentativas dentro da tolerancia usam media;
- tres tentativas usam mediana;
- tentativas brutas sao preservadas;
- dobras usam mm com precisao de 0,1;
- altura e perimetros usam cm com precisao de 0,1;
- peso usa kg com precisao de 0,1;
- calculo usa `Decimal`;
- arredondamento final para duas casas.

Limites operacionais:

- altura: 80,0 a 250,0 cm;
- peso: 15,0 a 400,0 kg;
- dobras: 1,0 a 80,0 mm;
- perimetros: 10,0 a 300,0 cm;
- gordura calculada: 0 a 75%.

## API

- `GET /api/v1/assessments/anthropometry/protocols`
- `POST /api/v1/assessments/members/{member_id}/anthropometry/preview`
- `POST /api/v1/assessments/members/{member_id}/anthropometry`
- `GET /api/v1/assessments/members/{member_id}/{assessment_id}/pdf`

Confirmacao exige header `Idempotency-Key: UUID` e usa restricao unica `(gym_id, idempotency_key)`.

## Acceptance criteria

1. Professor conclui avaliacao sem arquivo, OCR ou dado de bioimpedancia.
2. Peso e altura sao informados manualmente ou preenchidos pelo perfil.
3. Protocolo mostra somente medidas necessarias e perimetros opcionais separados.
4. Regras de repeticao e terceira tentativa sao aplicadas.
5. Backend calcula IMC, gordura, massa de gordura, massa livre, RCQ e TMB quando aplicavel.
6. Preview e confirmacao produzem mesmo resultado e hash.
7. Massa muscular e demais metricas nao calculaveis permanecem nulas.
8. PDF identifica modalidade, protocolo e versao, sem cards vazios.
9. Historico identifica antropometria e alerta comparacoes limitadas entre metodos/protocolos diferentes.
10. Clique duplicado nao cria duas avaliacoes nem duas reguas.
11. D+75 inicia reagendamento e D+90 representa vencimento.
12. D+8 e D+14 seguem como acompanhamento tecnico.
13. Bioimpedancia mantem comportamento, payload, relatorio e testes anteriores.
14. V1 pode ser ativada por `anthropometric_assessment_v1` sem depender do Actuar.
