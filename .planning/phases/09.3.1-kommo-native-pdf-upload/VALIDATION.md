# Validation

## Backend

- Token com `files` sobe e anexa PDF.
- Token sem `files` retorna erro claro.
- `native_file_required` nao aceita fallback silencioso.
- `native_file_preferred` registra fallback para link quando necessario.
- Reenvio nao duplica anexo valido para mesma origem.
- Multi-tenant preservado.

## Frontend

- Settings salva modo/fields.
- Bioimpedancia mostra CTA nativo e estados corretos.

## Validacao local

- `python -m compileall app`: passou.
- `pytest tests/test_kommo_file_service.py tests/test_body_composition_kommo_router.py -q`: 5 passed.
- `pytest tests/test_body_composition.py tests/test_report_service.py -q`: 26 passed.
- `alembic heads`: `20260515_0045 (head)`.
- `npm.cmd run lint`: passou.
- `npm.cmd run build`: passou.

## Piloto

- Configurar rota `body_composition`.
- Testar envio em aluno real com telefone.
- Confirmar na Kommo se lead recebeu arquivo anexado e Salesbot disparou.
