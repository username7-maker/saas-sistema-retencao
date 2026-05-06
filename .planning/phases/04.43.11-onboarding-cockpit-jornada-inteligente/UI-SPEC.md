# UI Spec

## Tela Principal

`Tarefas > Onboarding` passa a operar como Onboarding Cockpit.

## Informações no topo

- Alunos ativos em onboarding.
- Pendências esperadas até hoje.
- Atrasos.
- Sem responsável.
- Métrica de 2+ check-ins na primeira semana.
- Métrica de primeira avaliação D0-D30.

## Lista de Alunos

Cada aluno deve mostrar:

- Nome.
- Score.
- Plano.
- Dia da jornada.
- Fase atual.
- Próxima ação.
- Responsável sugerido.
- Turno preferido.

## Jornada

Etapas D0/D1/D3/D7/D15/D30 continuam visíveis, inclusive futuras. A diferença é que o `Modo execução` só mostra a etapa quando a janela operacional chegar.

## Estados

- Loading explícito.
- Empty state por turno.
- Erro claro ao carregar cockpit/score.
