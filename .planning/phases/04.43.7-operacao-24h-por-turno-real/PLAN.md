# Plano - 04.43.7 Operacao 24h por Turno Real

## Objetivo

Separar madrugada de noite e preparar a operacao diaria para quatro turnos reais, com fila saneada e historico preservado.

## Corte

1. Adicionar `overnight` nos contratos de usuario, aluno, tasks, Work Queue, retencao e avaliacoes.
2. Recalcular turno preferido por check-in usando 00-05 como madrugada.
3. Adicionar aliases `madrugada`, `noturno_madrugada` e `plantao_madrugada`.
4. Esconder tasks arquivadas das filas operacionais por padrao.
5. Criar preview/aplicar de saneamento operacional para manager/owner.
6. Expor `Madrugada` em filtros e formularios relevantes.
7. Registrar rotina operacional 24h e validar com testes.

## Fora do Escopo

- Escala completa de colaboradores.
- Envio automatico de mensagens.
- Exclusao/cancelamento em massa.
- Mudancas em integracoes externas.
