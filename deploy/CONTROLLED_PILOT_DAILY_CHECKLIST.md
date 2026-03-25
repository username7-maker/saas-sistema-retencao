# Controlled Pilot Daily Checklist

## Antes Da Equipe Entrar

- `GET /health/ready` responde `200`
- API esta sem scheduler
- worker esta ativo e processando jobs
- Redis esta acessivel
- nao ha erro repetido nos logs de API/worker
- aniversarios de hoje carregam
- retencao abre sem erro
- assessments abrem sem erro

## Inicio Do Dia

- conferir um import pequeno ou o ultimo import realizado
- conferir fila de retencao
- conferir tasks operacionais
- conferir requests recentes de recalc manual de risco
- conferir aniversarios de hoje

## Durante O Dia

- registrar qualquer permissao estranha por papel
- registrar tela que nao fecha o fluxo
- registrar atraso ou falha de job
- registrar se recepcao viu CTA que nao deveria
- registrar se trainer nao conseguiu concluir task-lite

## Fim Do Dia

- revisar incidentes do dia
- revisar se houve job preso
- revisar se houve erro repetido de websocket
- revisar se owner/manager precisaram improvisar fora do sistema
- decidir:
  - continua normal
  - continua com observacao
  - pausa piloto

## Indicadores Minimos

- imports do dia sem divergencia critica
- nenhum request de recalc perdido
- nenhum incidente de tenant
- recepcao sem bloqueio operacional grave
- trainer conseguindo operar o fluxo tecnico
