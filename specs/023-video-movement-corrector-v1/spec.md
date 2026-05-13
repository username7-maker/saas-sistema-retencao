# Spec 023 - Video Movement Corrector V1

## User Story

Como professor, quero analisar videos de execucao dos alunos com ajuda da IA, para preparar feedback tecnico mais rapido sem substituir minha revisao profissional.

## Requirements

- Criar settings por academia para o corretor de movimento por video.
- Manter recurso desligado por default.
- Exigir consentimento de imagem/video.
- Criar entidade tenant-scoped para review de video.
- Permitir upload ou referencia de video com validacao de tamanho, tipo e duracao.
- Gerar analise assistiva em modo `coach_review`.
- Bloquear casos sensiveis e baixa qualidade.
- Nunca enviar feedback automaticamente.
- Permitir professor aprovar/editar/rejeitar feedback.
- Integrar feedback aprovado ao Personal IA e Kommo.
- Registrar trilha em `TaskEvent`, `AutopilotAction` ou entidade de review.
- Expor historico no Perfil do Aluno e Coach Workspace.

## Non-goals

- Diagnostico medico.
- Fisioterapia automatizada.
- Prescricao autonoma de treino.
- Analise biomecanica clinica.
- Correcao em tempo real.
- App mobile nativo.

## Success Criteria

- Professor revisa video e entende feedback em ate 60 segundos.
- 100% dos casos sensiveis testados ficam bloqueados para revisao humana.
- Nenhum feedback e enviado sem aprovacao.
- Review e tenant-scoped e auditavel.

