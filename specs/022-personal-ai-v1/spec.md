# Spec 022 - Personal IA V1

## User Story

Como professor ou gestor, quero que o Cordex Gym OS prepare orientacoes personalizadas para alunos com base em avaliacao, bioimpedancia, metas, treino e historico real, para responder mais rapido sem substituir a revisao humana.

## Requirements

- Criar settings por academia para Personal IA.
- Manter `auto_send=false` na V1.
- Gerar contexto tecnico do aluno com dados reais e tenant-scoped.
- Preparar rascunhos de orientacao, nao prescricoes autonomas.
- Bloquear casos sensiveis e escalar para humano.
- Reusar Kommo como canal de preparo/handoff.
- Reusar Work Queue para excecoes e revisao humana.
- Registrar trilha em `AutopilotAction`, `AutopilotEvent` ou `TaskEvent`.
- Mostrar evidencias usadas na resposta.
- Medir drafts, bloqueios, aprovacoes e rejeicoes.

## Non-goals

- Prescrever treino autonomamente.
- Corrigir movimento por video.
- Criar dieta, suplemento ou aconselhamento medico.
- Enviar mensagem automaticamente.
- Criar app do aluno.
- Substituir professor.

## Success Criteria

- 60% dos drafts simples sao aproveitaveis com pouca edicao.
- 100% dos casos de dor/lesao/dieta/diagnostico testados bloqueiam resposta direta.
- Professor entende evidencias e acao em menos de 30 segundos.
- Nenhum draft e gerado sem `gym_id` e permissao correta.
