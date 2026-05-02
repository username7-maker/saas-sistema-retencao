# UI Spec - Retencao por Estagio

## Dashboard de Retencao

Trocar a leitura de fila unica por lanes operacionais:

- `Atencao agora`: 7-13 dias sem check-in.
- `Recuperar esta semana`: 14-29 dias.
- `Reativar 30+ dias`: 30-44 dias.
- `Escalar gerente`: 45-59 dias.
- `Base fria`: 60+ dias.

## Linha/Card

Cada item deve exibir:

- aluno;
- turno preferido;
- estagio operacional;
- severidade;
- churn;
- dias sem check-in;
- ultimo contato;
- score/forecast;
- acoes.

## Drawer/Playbook

O drawer deve ajustar a mensagem principal:

- `reactivation`: retorno guiado com professor.
- `manager_escalation`: gerente revisa permanencia, plano, trancamento ou cancelamento.
- `cold_base`: campanha de winback, fora da fila diaria comum.

## Work Queue

Mostrar badge de estagio de retencao e esconder `cold_base` da fila padrao `do_now`.
