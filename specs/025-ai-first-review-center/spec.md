# Spec 025 - AI First Review Center

## Summary
Criar uma central unica de revisao para todos os rascunhos e reviews AI First antes do envio humano pela Kommo.

## Requirements
- Agregar `AutopilotAction` das origens AI First existentes.
- Agregar `MovementVideoReview` relevante para revisao.
- Nao enviar autonomamente.
- Permitir preparar handoff Kommo quando o item estiver pronto e sem bloqueio.
- Permitir rejeitar item com motivo.
- Mostrar metricas por origem e status.
- Respeitar `gym_id` e papel do usuario.

## Sources
- `ai_service_agent`: `kommo_draft_reply`
- `personal_ai`: `personal_ai_guidance_draft`
- `student_personal_ai`: `student_personal_ai_kommo_draft`
- `movement_video`: `movement_video_feedback_draft`
- `movement_video_review`: `MovementVideoReview`

## Success Criteria
- Gestor abre uma tela e ve todos os rascunhos AI First pendentes.
- Professor consegue revisar video/Personal IA sem procurar em multiplas telas.
- Recepcao consegue revisar atendimento/aluno Kommo.
- Item bloqueado explica por que nao pode ser enviado.
- Acoes continuam supervisionadas e auditaveis.
