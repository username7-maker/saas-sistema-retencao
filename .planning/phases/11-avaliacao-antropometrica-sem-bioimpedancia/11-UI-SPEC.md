# Phase 11 - UI Spec

## Nova Avaliacao

Exibir dois caminhos:

- `Com bioimpedancia`: abre a aba legada de bioimpedancia.
- `Sem bioimpedancia`: abre formulario antropometrico.

## Formulario antropometrico

- data;
- peso;
- altura;
- sexo usado pela formula;
- idade;
- protocolo;
- medidas obrigatorias do protocolo;
- perimetros opcionais de acompanhamento;
- observacoes;
- botao de preview;
- confirmacao final.

## Output

- Preview calculado pelo backend.
- Aviso claro para metricas indisponiveis.
- `Massa muscular: indisponivel nesta modalidade`.
- Historico com badge `Antropometria`.
- PDF `Avaliacao antropometrica`.
