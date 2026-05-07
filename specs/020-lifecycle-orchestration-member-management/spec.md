# Spec 020 - Lifecycle Orchestration e Gestao de Alunos Expandida

## User Need

Como equipe da academia, eu preciso saber rapidamente em que momento operacional cada aluno esta, para agir com o cargo certo e sem misturar onboarding, rotina, retencao e reativacao.

## Requirements

- O sistema deve calcular lifecycle sem exigir preenchimento manual.
- O lifecycle deve respeitar onboarding D0-D30.
- Alunos 30+ dias sem check-in devem aparecer como reativacao.
- Alunos 60+ dias sem check-in devem aparecer como base fria.
- Cancelados e pausados devem sair da prioridade operacional comum.
- O Perfil Operacional deve expor lifecycle junto da proxima melhor acao.
- A lista de Membros deve exibir lifecycle, foco e dono sugerido.
- Nenhuma regra deve criar envio automatico.

## Non Goals

- Persistir historico de lifecycle.
- Criar app do aluno.
- Reescrever Work Queue.
- Criar automacao autonoma.

## Acceptance

- Lifecycle aparece em `GET /api/v1/members/`.
- Lifecycle aparece em `GET /api/v1/members/{id}/operational-profile`.
- Frontend mostra badge e foco no modulo Membros.
- Testes cobrem os principais estados.
