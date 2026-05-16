# Spec 016 - Bioimpedancia unificada a avaliacao tecnica

## User Story

Como professor e gestor, quero que uma bioimpedancia conte como avaliacao tecnica do aluno e gere a mesma rotina de acompanhamento, para nao perder treino entregue, feedback e reavaliacao apenas porque o registro veio pela bioimpedancia.

## Requisitos Funcionais

- RF1: Bioimpedancia salva deve criar a regua tecnica D+8, D+14 e D+90.
- RF2: Avaliacao formal deve continuar criando a mesma regua.
- RF3: O sistema deve manter uma unica regua ativa por aluno/ciclo tecnico quando formal e bioimpedancia ocorrerem juntas.
- RF4: `Task.extra_data` deve informar `assessment_source_type`.
- RF5: Quando houver mais de uma fonte no ciclo, `Task.extra_data.assessment_sources` deve listar ambas.
- RF6: Bioimpedancia deve contar como avaliacao realizada no onboarding score.
- RF7: Bioimpedancia deve contar como cobertura tecnica na fila de avaliacao pendente.
- RF8: Endpoints de bioimpedancia devem aceitar opcao para nao sincronizar Actuar.
- RF9: Frontend deve oferecer `Salvar apenas no sistema` e preservar `Salvar e enviar ao Actuar`.
- RF10: Relatorio premium de bioimpedancia deve exibir o logo ProGym ao lado da marca Cordex Gym OS.
- RF11: Work Queue deve enviar primeira avaliacao para operacao/recepcao e tarefas tecnicas para professor.

## Requisitos Nao Funcionais

- RNF1: Nenhuma task duplicada deve ser criada por reprocessamento.
- RNF2: Tenant isolation deve ser preservado.
- RNF3: Historico concluido nao deve ser apagado.
- RNF4: Nenhum envio externo automatico sera criado nesta fase.

## Criterios de Aceite

- CA1: Salvar bioimpedancia gera tres tasks tecnicas.
- CA2: Salvar formal + bio no mesmo ciclo nao duplica etapa.
- CA3: Aluno com bioimpedancia nao aparece como sem avaliacao registrada.
- CA4: Botao local nao cria tentativa Actuar.
- CA5: Botao Actuar preserva sync.
- CA6: Professor nao recebe task de primeira avaliacao.
- CA7: Professor recebe D+8/D+14/D+90 tecnicos.
- CA8: Relatorio premium mostra ProGym + Cordex Gym OS no cabecalho.
