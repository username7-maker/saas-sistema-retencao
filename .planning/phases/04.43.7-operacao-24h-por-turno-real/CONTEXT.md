# Contexto - 04.43.7 Operacao 24h por Turno Real

## Problema

O piloto opera com academia 24h, mas o sistema ainda tratava noite e madrugada como o mesmo bloco operacional. Isso confundia fila, responsaveis e rotina de execucao, especialmente em Tasks, Work Queue, Retencao, Avaliacoes, Membros e Usuarios.

## Decisoes

- `overnight` e o valor canonico de madrugada.
- UI exibe `Madrugada`.
- Faixas oficiais:
  - `overnight`: 00:00-05:59
  - `morning`: 06:00-11:59
  - `afternoon`: 12:00-17:59
  - `evening`: 18:00-23:59
- Tasks antigas de baixo valor saem da operacao por arquivamento operacional, sem deletar nem cancelar.

## Guardrails

- Sem exclusao fisica em massa.
- Sem alterar status de task apenas para limpar fila.
- Inadimplencia, jornadas ativas e onboarding D0-D30 ficam protegidos.
- Manager/owner revisa todos os turnos; operador usa `Meu turno`.
