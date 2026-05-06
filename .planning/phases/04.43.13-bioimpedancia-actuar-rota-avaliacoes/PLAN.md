# Plano

## Objetivo

Tratar bioimpedancia como parte do mesmo ciclo tecnico da avaliacao formal, criando as mesmas tarefas D+8, D+14 e D+90 e removendo falsos pendentes de primeira avaliacao.

## Implementacao

1. Extrair helper unico da regua tecnica pos-avaliacao.
2. Chamar o helper ao salvar avaliacao formal com `assessment_source_type=formal_assessment`.
3. Chamar o helper ao salvar/atualizar/revisar bioimpedancia com `assessment_source_type=body_composition`.
4. Deduplicar regua por aluno, etapa e vencimento do ciclo tecnico.
5. Incluir `assessment_sources` no `Task.extra_data` quando formal e bioimpedancia coexistirem.
6. Fazer analytics de avaliacao considerar formal ou bioimpedancia como cobertura tecnica.
7. Fazer score de onboarding considerar bioimpedancia dentro da janela D0-D30.
8. Ajustar Work Queue para separar primeira avaliacao da fila do professor.
9. Adicionar flag `sync_actuar` nos endpoints de bioimpedancia.
10. Adicionar botao `Salvar apenas no sistema` no frontend.
11. Adicionar logo ProGym no relatorio premium.

## Regras de roteamento

- `Agendar primeira avaliacao`: dominio `assessment`, responsavel operacional/recepcao.
- `Verificar treino`, `Registrar feedback`, `Agendar reavaliacao`: dominio `trainer`, responsavel professor/coach.
- Bioimpedancia entra no mesmo fluxo tecnico, mas nao cria tarefa duplicada se avaliacao formal do mesmo ciclo ja criou a etapa.

## Validacao

- Testes focados de backend em avaliacao, bioimpedancia, onboarding score, assessment queue, Work Queue e relatorio.
- Build/frontend tests focados para o botao de bioimpedancia.
- Validacao manual no piloto: salvar bioimpedancia sem Actuar, salvar com Actuar e conferir fila do professor/operacao.
