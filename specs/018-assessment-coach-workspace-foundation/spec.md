# Spec 018 - Assessment + Coach Workspace Foundation

## User Story

Como professor da academia, quero abrir uma fila tecnica do meu turno para saber quais alunos precisam de acompanhamento de treino, avaliacao, bioimpedancia, feedback ou reavaliacao, para agir rapidamente sem misturar minha rotina com tarefas de recepcao, retencao ou comercial.

## Requirements

- O sistema deve criar uma superficie staff-first para professor.
- A fila tecnica deve respeitar turno do login e turno preferido do aluno.
- A fila deve usar dados reais de avaliacao, bioimpedancia, tasks tecnicas e Perfil 360.
- O professor deve ver apenas a proxima acao tecnica e evidencias essenciais.
- Managers/owners devem poder alternar para todos os turnos.
- Receptionists nao devem receber fila tecnica por padrao.
- Primeira avaliacao operacional deve continuar com recepcao/operacao quando for etapa de agendamento, nao professor.
- A regua tecnica D+8/D+14/D+90 deve aparecer como tarefa do professor quando a janela estiver aberta.
- Bioimpedancia deve alimentar o ciclo tecnico igual avaliacao formal quando exigir acompanhamento.
- Retencao comum, inadimplencia e comercial nao devem poluir a fila tecnica.

## Non-goals

- App do aluno.
- Prescricao automatica de treino.
- Diagnostico medico.
- IA generativa decidindo treino.
- Agenda completa de aulas.
- Comissao/ponto/escala de equipe.
- Reescrever Perfil 360.

## Success Criteria

- Professor consegue entender o item e iniciar acao em ate 20 segundos.
- Fila tecnica mostra apenas itens do turno por padrao.
- D+8, D+14 e D+90 aparecem com CTA correto.
- Bioimpedancia recente deixa claro quando exige revisao tecnica.
- Tasks de recepcao e retencao nao aparecem na fila do professor.
- Gestor consegue revisar gargalos por turno.

## Constraints

- O backend permanece fonte da verdade.
- Toda leitura deve ser tenant-scoped.
- Toda acao relevante deve registrar `TaskEvent` ou outcome existente.
- Sem envio automatico externo nesta fase.
- Sem dados tecnicos inventados quando nao houver base.
