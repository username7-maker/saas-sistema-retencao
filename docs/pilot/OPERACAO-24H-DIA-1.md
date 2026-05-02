# Operacao 24h - Dia 1 do Piloto

Data alvo: 30/04/2026
Academia: AI GYM OS Piloto

## Status operacional preparado

- Turno preferido dos alunos recalculado por check-ins.
- Turno `Madrugada` ativo na base.
- Usuarios operacionais configurados por turno.
- Owner mantido como supervisao geral para enxergar todos os turnos.
- Nenhuma task foi deletada ou cancelada.

## Distribuicao atual

| Turno | Operadores | Tasks abertas | Vencidas | Regra do Dia 1 |
|---|---:|---:|---:|---|
| Madrugada | 1 | 194 | 12 | Executar ate 25 acoes nao invasivas |
| Manha | 2 | 554 | 34 | Executar ate 50 acoes totais |
| Tarde | 2 | 661 | 37 | Executar ate 50 acoes totais |
| Noite | 1 | 830 | 59 | Executar ate 25 acoes e sinalizar gargalo |
| Sem turno | Owner/gerencia | 571 | 63 | Triagem separada, nao misturar com fila dos turnos |

## Como cada turno deve operar

1. Entrar em `/tasks`.
2. Usar `Modo execucao`.
3. Manter filtro `Meu turno`.
4. Executar somente o lote priorizado do turno.
5. Registrar resultado em cada acao.
6. Adiar quando houver combinado real.
7. Encaminhar quando depender de outro cargo.
8. Nao tentar zerar backlog antigo no Dia 1.

## Limite operacional

- Limite por operador: 25 acoes/dia.
- Manha: ate 50 acoes.
- Tarde: ate 50 acoes.
- Noite: ate 25 acoes.
- Madrugada: ate 25 acoes.
- Owner/gerencia: ate 25 acoes de `Sem turno` para classificar ou encaminhar.

## Regras para madrugada

A madrugada deve executar apenas:

- observacoes internas;
- verificacao de aluno recorrente;
- registro de contexto;
- follow-up nao invasivo;
- encaminhamento para proximo turno.

Nao executar na madrugada:

- cobranca ativa;
- ligacao;
- mensagem comercial agressiva;
- reativacao sensivel;
- abordagem que possa incomodar aluno fora de horario.

## Passagem de plantao

No fim de cada turno, o responsavel deve informar ao gerente:

- quantas acoes executou;
- quantas ficaram pendentes;
- quais casos foram encaminhados;
- quais alunos responderam;
- quais mensagens deram erro ou ficaram confusas.

## Criterio de sucesso do Dia 1

O Dia 1 sera considerado valido se:

- cada operador conseguir abrir sua fila sem ajuda tecnica;
- cada operador executar pelo menos 10 acoes reais;
- cada acao tiver resultado registrado;
- gerente conseguir alternar para todos os turnos;
- `Sem turno` nao contaminar a fila principal;
- nenhum usuario tentar resolver todas as tasks antigas.

## Risco atual

O piloto e viavel como operacao assistida, mas nao como go-live completo. O principal risco e volume acumulado: 2.810 tasks abertas/em andamento. A noite e o maior gargalo e precisa de reforco ou triagem gerencial.
