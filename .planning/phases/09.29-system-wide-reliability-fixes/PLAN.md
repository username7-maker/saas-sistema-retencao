# Correcoes de confiabilidade da revisao geral

## Objetivo

Corrigir os achados confirmados na revisao geral de 16/09/2026 sem ampliar o
escopo funcional do produto.

## Escopo

- limpar consultas e dados derivados quando a identidade autenticada muda;
- usar uma data estavel para vendas e limites semanais sem sobreposicao;
- levar os atalhos do cockpit ao lead, aluno ou tarefa selecionados;
- limitar a espera da captura fotografica, compactar imagens grandes antes do
  preparo e congelar os controles durante a confirmacao;
- cobrir cada regressao com testes focados e executar lint/build e suites
  relevantes antes da publicacao.

## Fora do escopo

- provisionar secrets do GitHub, que exige credenciais externas;
- calibracao em cameras fisicas, que continua sendo um gate do piloto.
