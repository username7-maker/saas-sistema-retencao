# Phase 11 - Research

## Decisions

- Usar protocolos antropometricos publicos ja modelados no sistema quando `supported`.
- Manter massa muscular indisponivel, porque massa livre de gordura nao e sinonimo de massa muscular.
- Usar Mifflin-St Jeor apenas como TMB estimada para adultos de 19 a 78 anos.
- Persistir `anthropometry_snapshot_json` na V1 em vez de normalizar tentativas em tabelas separadas.
- Registrar origem por indicador no snapshot.

## Measurement policy

`anthropometry-v1`:

- duas tentativas obrigatorias;
- terceira tentativa quando tolerancia for excedida;
- media de duas dentro da tolerancia;
- mediana de tres;
- preservacao de todas as tentativas;
- validacao de lado, unidade, precisao e limites plausiveis.
