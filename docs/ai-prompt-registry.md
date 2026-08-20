# AI Prompt Registry

O AI First OS usa prompts versionados por agente especialista para gerar textos supervisionados.

## Modelo padrao
`OPENAI_SPECIALIST_MODEL=gpt-4.1-mini`

`OPENAI_MODEL` e `OPENAI_VISION_MODEL` continuam disponiveis para fluxos legados, baratos ou OCR/visao.

## Prompts V1
- `body_composition_coach_v1`
- `body_composition_student_v1`
- `assessment_coach_v1`
- `assessment_student_v1`
- `personal_ai_coach_v1`
- `student_personal_ai_v1`
- `kommo_service_agent_v1`
- `movement_video_feedback_v1`

## Guardrails
- Nenhum fluxo ganha autoenvio nesta fase.
- OCR continua extrator, sem persona de musculacao.
- Autopilot safety/policy/resolver continuam deterministicos.
- Video continua `coach_review`.
- Dor, lesao, cancelamento, reclamacao, opt-out e contestacao financeira escalam para humano.

## Metadata
Outputs e drafts devem carregar:
- `prompt_key`
- `prompt_version`
- `model`
- `safety_profile`
- `generated_at`
- `fallback_used`
