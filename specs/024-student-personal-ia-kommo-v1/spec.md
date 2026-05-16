# Spec 024 - Student Personal IA Kommo V1

## Summary
Aluno aciona Personal IA e envia video pelo canal Kommo. O Cordex Gym OS gera rascunho/review supervisionado para a equipe responder pela Kommo. V1 nao envia automaticamente.

## Requirements
- Kommo webhook deve registrar inbound e resolver aluno por `KommoMemberLink`.
- Mensagens tecnicas devem criar `AutopilotAction` com `action_type=student_personal_ai_kommo_draft`.
- Videos devem criar `MovementVideoReview` com `metadata_json.source=student_kommo`.
- `auto_send` deve permanecer `false`.
- Guardrails obrigatorios: consentimento, opt-out/atividade humana recente, Kommo pronta, limites diarios, casos sensiveis e consentimento de imagem para video.
- Work Queue deve expor `source_type=student_personal_ai`.
- Settings devem permitir ativar/desativar a feature por academia.

## Success Criteria
- Aluno envia pergunta tecnica via Kommo e aparece rascunho na fila.
- Aluno envia video via Kommo e aparece review supervisionado.
- Sem consentimento ou Kommo nao pronta vira bloqueio explicavel.
- Nenhuma resposta e enviada sem humano.
