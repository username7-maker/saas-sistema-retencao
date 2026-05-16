# Status

- Estado: implementado e validado localmente.
- Data: 2026-05-15.
- Piloto alvo: ProGym.

## Checkpoints

- [x] Migration criada.
- [x] Servico Files API criado.
- [x] Settings estendido.
- [x] Salesbot integrado com PDF nativo.
- [x] Bioimpedancia usando nativo por padrao.
- [x] Testes e build executados.

## Validacoes executadas

- `python -m compileall app`
- `pytest tests/test_kommo_file_service.py tests/test_body_composition_kommo_router.py -q`
- `pytest tests/test_body_composition.py tests/test_report_service.py -q`
- `alembic heads`
- `npm.cmd run lint`
- `npm.cmd run build`
