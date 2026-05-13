# Spec 023 Plan - Video Movement Corrector V1

## Technical Approach

Reusar a fundacao tecnica do Coach Workspace, Perfil 360, Personal IA, Kommo, TaskEvent e AutopilotAction. A V1 cria uma camada de review de video supervisionada, com processamento assistivo e fallback honesto quando analise automatica nao estiver configurada.

## Backend

- `MovementVideoReview` model e migration `20260507_0041`.
- `schemas/movement_video.py`.
- `services/movement_video_service.py`, com guardrails e fallback manual na V1.
- Analise automatica real fica fora desta wave; o estado atual e `manual_observation` para evitar diagnostico falso.
- `settings/movement-video-ai`.
- Endpoints:
  - `GET /api/v1/settings/movement-video-ai`;
  - `PUT /api/v1/settings/movement-video-ai`;
  - `POST /api/v1/members/{member_id}/movement-video/reviews`;
  - `GET /api/v1/members/{member_id}/movement-video/reviews`;
  - `POST /api/v1/movement-video/reviews/{id}/analyze`;
  - `POST /api/v1/movement-video/reviews/{id}/approve`;
  - `POST /api/v1/movement-video/reviews/{id}/prepare-kommo`;
  - `POST /api/v1/movement-video/reviews/{id}/reject`.

## Frontend

- Settings para owner/manager.
- Card no Coach Workspace.
- Secao no Perfil 360.
- Estados para upload, analise, bloqueio, revisao e aprovado.
- CTAs supervisionados.

## Data

Campos minimos:

- `gym_id`;
- `member_id`;
- `trainer_user_id`;
- `exercise_name`;
- `status`;
- `analysis_status`;
- `video_asset_url` ou referencia segura;
- `summary`;
- `detected_points`;
- `suggested_feedback`;
- `coach_feedback`;
- `blocked_reasons`;
- `metadata_json`.

## Rollout

1. Settings desligado.
2. Criar reviews manuais sem IA.
3. Ativar analise assistiva para professores internos.
4. Preparar feedback aprovado na Kommo.
5. Validar 10 videos reais.

## Implemented In Wave 1

- Settings `GET/PUT /api/v1/settings/movement-video-ai`.
- Reviews por aluno em `/api/v1/members/{member_id}/movement-video/reviews`.
- Acoes supervisionadas: `analyze`, `approve`, `reject`, `prepare-kommo`.
- Guardrails: feature flag, consentimento de imagem, referencia obrigatoria, media type, tamanho e duracao.
- Sem upload binario e sem armazenamento de original por padrao.
- Feedback aprovado cria `AutopilotAction` `movement_video_feedback_draft` e pode preparar handoff Kommo.

## Implemented In Wave 2 Partial

- Aba `Video IA` em Settings para owner/manager.
- Service frontend `movementVideoService`.
- Painel no Coach Workspace para professor criar review por URL segura, preparar revisao, editar/aprovar feedback e preparar Kommo.
- Perfil 360/historico completo fica como proxima fatia.
