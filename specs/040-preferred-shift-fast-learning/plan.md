# Plan 040 - Preferred Shift Fast Learning

## Technical Plan
1. Registrar fase GSD 09.10 e Spec Kit 040.
2. Reduzir `PREFERRED_SHIFT_LOOKBACK_DAYS` para 30.
3. Simplificar derivacao para vencedor unico por contagem recente.
4. Quando houver check-ins recentes mas empate, gravar `None` em vez de manter fallback antigo.
5. Hidratar membros sem turno na Work Queue usando check-ins recentes antes de mapear os cards.
6. Atualizar testes focados e validar.

## Risk Control
- Manter aliases de turno existentes.
- Preservar fallback manual apenas quando nao houver nenhum check-in recente.
- Nao adicionar migration.
