# Spec 022 Plan - Personal IA V1

## Technical Approach

Reusar a arquitetura existente de assessment, body composition, goals, training plans, Coach Workspace, Kommo, Autopilot e Work Queue. A V1 adiciona um service de Personal IA que prepara orientacoes supervisionadas.

## Backend

- `personal_ai_service.py`
- `personal_ai_safety_service.py`
- `personal_ai_prompt_service.py`
- `personal_ai_context_service.py`
- Settings em `GymAutopilotSettings.extra_data.personal_ai` ou tabela dedicada se a estrutura crescer.
- Reusar `AutopilotAction` com `action_type=personal_ai_guidance_draft`.
- Endpoints:
  - `GET /api/v1/settings/personal-ai`
  - `PUT /api/v1/settings/personal-ai`
  - `GET /api/v1/members/{member_id}/personal-ai/context`
  - `POST /api/v1/members/{member_id}/personal-ai/drafts`
  - `GET /api/v1/personal-ai/drafts`
  - `POST /api/v1/personal-ai/drafts/{id}/prepare-kommo`

## Frontend

- Bloco `Personal IA` no perfil/Coach Workspace.
- Itens `Personal IA` na Work Queue.
- Settings para owner/manager.
- CTAs: gerar, preparar na Kommo, copiar, rejeitar, encaminhar professor.

## Data

Preferir dados existentes:

- `Assessment`
- `BodyCompositionEvaluation`
- `MemberGoal`
- `TrainingPlan`
- `MemberConstraints`
- `Task`
- `TaskEvent`
- `AutopilotAction`
- `MessageLog`

## Rollout

1. Settings desligados por padrao.
2. Habilitar para professores/owner no piloto.
3. Gerar drafts internos sem Kommo.
4. Preparar na Kommo com revisao humana.
5. Medir aproveitamento e bloqueios.

