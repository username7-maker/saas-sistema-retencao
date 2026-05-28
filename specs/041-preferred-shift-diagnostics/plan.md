# Plan 041 - Preferred Shift Diagnostics

## Scope
Adicionar diagnostico explicavel para `Sem turno` na Work Queue, mantendo o aprendizado rapido da fase 040.

## Implementation
1. Criar helper em `preferred_shift_service` para montar diagnostico a partir das contagens recentes.
2. Reutilizar a consulta de check-ins recentes da hidratacao de turno para tambem retornar diagnosticos.
3. Estender `WorkQueueItemOut` com campos opcionais:
   - `preferred_shift_status`
   - `preferred_shift_reason`
   - `preferred_shift_counts`
4. Passar diagnostico em itens de task e nos retornos de task onde houver `db`.
5. Atualizar tipos do frontend.
6. Mostrar o motivo abaixo do badge de turno apenas quando o turno estiver indefinido.
7. Adicionar testes focados.

## Validation
- `specify check`
- `python -m pytest tests/test_preferred_shift_service.py tests/test_work_queue_service.py`
- `npm run test -- WorkExecutionView`
- `npm run lint`
- `npm run build`

## Deployment
Publicar backend e frontend no piloto se os testes passarem.
