# Personal IA V1

## Visao geral

O Personal IA V1 e uma camada assistiva para professores. Ele usa contexto real do aluno para preparar rascunhos tecnicos supervisionados, sem prescrever treino de forma autonoma e sem enviar mensagem automaticamente.

## Escopo da V1

- Modo unico: `coach_review`.
- Autoenvio: sempre `false`.
- Publico operacional: `owner`, `manager` e `trainer`.
- Contexto usado: cadastro do aluno, turno, risco, avaliacao formal, bioimpedancia, treino ativo, metas, restricoes, check-ins recentes e tasks tecnicas.
- Saida: rascunho curto, evidencia usada, bloqueios e proxima acao.

## Guardrails

O Personal IA bloqueia ou escala quando encontra:

- dor, lesao ou emergencia;
- pedido medico ou medicacao;
- dieta, suplemento ou orientacao nutricional;
- cancelamento, reclamacao ou assunto sensivel;
- pedido de prescricao autonoma de treino;
- aluno sem treino ativo quando a pergunta exige orientacao de treino;
- falta de avaliacao/bioimpedancia quando a pergunta exige base tecnica.

## Endpoints

- `GET /api/v1/settings/personal-ai`
- `PUT /api/v1/settings/personal-ai`
- `GET /api/v1/members/{member_id}/personal-ai/context`
- `POST /api/v1/members/{member_id}/personal-ai/drafts`
- `GET /api/v1/personal-ai/drafts`
- `POST /api/v1/personal-ai/drafts/{draft_id}/prepare-kommo`

## Rollout recomendado

1. Ativar `enabled=true` apenas para professores/gestores.
2. Gerar rascunhos para alunos com avaliacao ou bioimpedancia recente.
3. Revisar manualmente 20 rascunhos antes de usar com alunos.
4. Preparar na Kommo apenas quando o professor assumir a revisao.
5. Manter video, prescricao autonoma e dieta fora da V1.

## Validacao manual

1. Abrir Configuracoes > Personal IA e ativar.
2. Usar um aluno com treino ativo e bioimpedancia/avaliacao.
3. Chamar `POST /members/{id}/personal-ai/drafts` com uma pergunta de rotina.
4. Confirmar que o rascunho fica `draft_ready`.
5. Testar pergunta com "dor forte" e confirmar que fica `escalated`.
6. Testar pergunta "monte um treino novo" e confirmar bloqueio de prescricao autonoma.

## Student Personal IA via Kommo

A fase `08.7` leva a entrada do aluno para a Kommo. O aluno pode mandar pergunta tecnica ou video na conversa Kommo; o AI Gym OS prepara rascunho/review para revisao humana.

Endpoints:

- `GET /api/v1/settings/student-personal-ai`
- `PUT /api/v1/settings/student-personal-ai`
- `GET /api/v1/ai/student-personal/drafts`
- `POST /api/v1/ai/student-personal/drafts/{draft_id}/prepare-kommo`
- `POST /api/v1/ai/student-personal/drafts/{draft_id}/reject`

Defaults seguros:

- `enabled=false`
- `mode=draft_only`
- `auto_send_enabled=false`
- `kommo_required=true`
- consentimento de comunicacao para texto
- consentimento de imagem para video

Videos usam `MovementVideoReview` com `metadata_json.source=student_kommo`. Sem storage novo na V1: quando a Kommo nao entrega URL recuperavel, o review marca `needs_media_retrieval` e orienta a equipe a abrir a conversa original.
