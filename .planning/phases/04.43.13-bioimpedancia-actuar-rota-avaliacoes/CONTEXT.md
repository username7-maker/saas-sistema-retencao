# 04.43.13 - Bioimpedancia unificada a regua tecnica pos-avaliacao

## Contexto

A academia usa avaliacao fisica formal e bioimpedancia como evidencias tecnicas do ciclo do aluno. Antes desta fase, a regua tecnica pos-avaliacao estava ligada principalmente a avaliacao formal, enquanto bioimpedancia ficava mais como registro/laudo. Isso causava dois problemas operacionais:

- Alunos com bioimpedancia podiam continuar aparecendo como "sem avaliacao registrada".
- Professores nao recebiam automaticamente os compromissos tecnicos D+8, D+14 e D+90 apos uma bioimpedancia.

## Decisao

Bioimpedancia e avaliacao formal passam a alimentar o mesmo ciclo tecnico do aluno. A bioimpedancia conta como avaliacao realizada e tambem cria a regua tecnica pos-avaliacao, sem duplicar tarefas quando os dois registros ocorrerem no mesmo ciclo.

## Escopo

- Unificar criacao de tasks tecnicas para avaliacao formal e bioimpedancia.
- Permitir salvar bioimpedancia sem sincronizar Actuar.
- Manter "Salvar e enviar ao Actuar" como comportamento disponivel.
- Fazer bioimpedancia contar no score de onboarding e na fila de avaliacao pendente.
- Corrigir roteamento: primeira avaliacao fica com operacao/recepcao; professor recebe compromissos tecnicos.
- Adicionar logo ProGym no relatorio premium de bioimpedancia.

## Fora de escopo

- Envio automatico de WhatsApp.
- Mudanca do contrato de laudo tecnico completo.
- Criacao de novo modelo de ciclo tecnico persistido.
- Backfill completo em massa de bioimpedancias antigas.
