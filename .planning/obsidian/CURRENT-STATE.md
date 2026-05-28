# Current State

## 2026-05-28 - User Avatar And Team Identity Upload 04.35
Fase 04.35 reaberta e publicada no piloto apos a 09.15/4.34. O foco foi identidade de equipe: upload real de avatar como caminho principal, cargo/foto como informacao de exibicao e `role` como permissao. Decisao V1: manter persistencia no campo `users.avatar_url` em data URL enquanto o piloto nao possui object storage/volume persistente dedicado para uploads da API; URL manual virou fallback, nao caminho principal. Validacao: Spec Kit OK, backend 18 passed, frontend focado 10 passed, lint/build OK. Publicado com Vercel `dpl_6qt2W98qVm4ZLWvABMSme1ofM3WH`, Railway API `f050c8a7-9ccf-4bb5-82fe-f4e271e42eb9` e worker `c240b7bf-4c10-48ba-9bc2-b70aa144282d`; smoke `/settings`, API health e logs pos-deploy OK.

## 2026-05-27 - Pilot Admin Surfaces Closure 09.15
Fase 09.15 aberta para reativar a Phase 4.34 (`Superficies administrativas e relatorios do piloto`) em cortes pequenos depois dos hotfixes de auth/admin, tasks, retencao, Kommo e Resend. Primeiro corte: o disparo mensal de relatorios passa a receber `gym_id` e filtrar destinatarios OWNER/MANAGER pela mesma academia, reduzindo risco de envio cross-tenant. Tambem foi alinhado o RBAC frontend de `/notifications` para permitir `trainer`, como o backend ja permite. Metas, NPS e Notificacoes ganharam testes focados para empty states/acoes administrativas. Validacao local: Spec Kit OK, backend focado 15 passed, frontend admin focado 12 passed, lint/build OK e `py_compile` OK. Publicado no piloto com Vercel `dpl_377T7QaFGSUfH9w5SPYgbv6y9CvZ`, Railway API `88553164-6107-4860-bf56-37461269b9a7` e Railway worker `c224feb7-c7d4-42f7-bf4b-15540f2a2f6b`; smoke `/`, `/tasks`, API health e logs pos-deploy OK.

## 2026-05-27 - Resend Email Provider 09.14
Fase 09.14 publicada no piloto para substituir o envio transacional de e-mails por Resend. O backend agora usa `RESEND_API_KEY`, `RESEND_SENDER`, `RESEND_REPLY_TO` e `httpx` para reset de senha, convite de usuario e anexos. SendGrid saiu dos requirements e das configuracoes ativas. Validacao: Spec Kit OK, backend focado 114 passed, compileall OK, API Railway `d9630b88-5557-41af-beb2-9f38a5356efa`, worker Railway `82e0bb92-f9c6-49fe-8943-c96c08be0a95`, health OK e `forgot-password` chamou Resend com `HTTP/1.1 200 OK`. Pendente: rotacionar a chave colada no chat e verificar DNS de `cordex.com` antes de usar remetente do dominio.

## 2026-05-27 - Retention UI Profile Cleanup 09.13
Fase 09.13 implementada e publicada no piloto para organizar a superficie de retencao sem mudar contratos backend: drawer de playbook com sinais compactos e barra fixa de acoes, aba Retencao do drawer de aluno com contraste dark-safe, e Perfil 360 sem os paineis Cordex Coach/Video de Movimento temporariamente. Validacao: Spec Kit OK, testes focados 10 passed, lint/build OK. Publicado com Vercel `dpl_8jv2HQFUGak6G8VUhxKuyWn7B9qN`; smoke do alias `https://saas-frontend-pearl.vercel.app` e assets principais OK.

## 2026-05-27 - Kommo Professor Pipeline Routing 09.12
Fase 09.12 implementada e publicada no piloto para permitir pipeline Kommo por professor somente em operacoes tecnicas. O backend agora tem `kommo_trainer_routes`, settings Kommo le/salva `trainer_routes`, e o resolvedor tenta rota do professor via `Member.assigned_user_id` para `assessment`, `body_composition`, `student_ai` e alias `trainer`; quando falta rota completa, cai na rota de dominio como fallback de coordenacao. Dominios nao tecnicos continuam por dominio. A tela Configuracoes > Kommo ganhou "Pipelines por professor" com status pronto/incompleto/desativado. Validacao: Spec Kit OK, Alembic head OK, migration aplicada no Railway, backend Kommo focado 18 passed, frontend Kommo 2 passed, lint/build OK. Publicado com Railway `22babda6-187d-45a2-8a3b-fdd7b960bb16` e Vercel `dpl_FxBY5nMfua6HTEVch7e8JVBgt69T`; health e smoke `/settings` OK.

## 2026-05-27 - Preferred Shift Diagnostics 09.11
Fase 09.11 implementada e publicada no piloto para explicar por que um item da fila aparece como `Sem turno`. A Work Queue agora envia diagnostico opcional (`preferred_shift_status`, `preferred_shift_reason`, `preferred_shift_counts`) e Tasks mostra o motivo apenas quando o turno esta indefinido: sem check-in recente/importado nos ultimos 30 dias ou empate com contagens por turno. Validacao: Spec Kit OK, backend focado 33 passed, frontend focado 9 passed, lint/build OK. Publicado com Railway `40133508-b5a2-44eb-a134-a0d42f242fe7` e Vercel `dpl_FYPsHMv6pCBkpyacdrzBn4HbhhyG`; health e smoke `/tasks` OK.

## 2026-05-27 - Preferred Shift Fast Learning 09.10
Fase 09.10 implementada e publicada no piloto para tornar a inferencia de turno preferido mais rapida para alunos novos: janela de 30 dias, 1 check-in define turno, empate limpa e 2 de 3 vence. Work Queue tambem hidrata alunos sem turno salvo a partir de check-ins recentes antes de montar os cards. Validacao: Spec Kit OK e backend focado 30 passed. Publicado com Railway `8a136b2d-dba4-42c1-a740-8765e42b6fe2`; health OK. Sync manual pos-deploy retornou `updated_total=0`, sugerindo que alunos ainda sem turno nao tem check-in recente registrado ou estao empatados pela nova regra.

## 2026-05-27 - Tasks Execution Subfilters 09.9
Fase 09.9 implementada e publicada no piloto para adicionar filtros secundarios na fila `/tasks`: Onboarding por janela de jornada (`Dia 0`, `Dia 1`, `Dia 2-6`, `Dia 7+`), Retencao por categoria/estagio e Professor por etapa tecnica. A V1 usa bucket operacional canonico na Work Queue, sem migration e sem alterar RBAC. Validacao: Spec Kit OK, backend work queue 23 passed, frontend inbox IA 8 passed, lint/build OK. Publicado com Railway `c0260823-06d9-482b-840a-dd3b368e7e13` e Vercel `dpl_BxPeoFsprDRwJAaCfrrD6cL3D2PP`; smoke em `/tasks` e asset publicado OK.

## 2026-05-26 - Cordex UX/Auth/Admin Hardening 09.8
Fase 09.8 implementada e publicada no piloto para reduzir poluicao visual conservadoramente no Cordex Gym OS, tornar reset de senha acessivel no login e simplificar criacao/reset administrativo de usuarios com senha provisoria auto-gerada. Validacao: Spec Kit OK, backend focado 59 passed, frontend focado 12 passed, lint/build OK, Railway API health OK, Vercel pilot smoke OK.

Hotfix no mesmo dia: recuperacao por e-mail esta chegando ao backend, mas o SendGrid recusou o envio no provedor. O sistema agora registra a razao operacional do bloqueio sem expor segredo e oferece troca de senha autenticada em Configuracoes > Seguranca. Validacao do hotfix: backend 61 passed, frontend focado 10 passed, Spec Kit/lint/build OK. Publicado com Railway `859216ce-00af-49e8-a244-707ab845c661` e Vercel `dpl_GoexNbNP9rQALQTCwXa73FnzF8Bk`.

Segundo hotfix: criacao de usuario mudou para convite de definicao de senha como padrao. Senha provisoria agora so e gerada quando o admin escolhe explicitamente `Gerar senha provisoria agora`; se o convite por e-mail falhar, a criacao faz rollback em vez de deixar conta sem acesso. Validacao: backend 66 passed, frontend focado 11 passed, Spec Kit/lint/build OK. Publicado com Railway `4495a1f9-91ef-4ecf-a984-c2eef9ececd3` e Vercel `dpl_58EB5NyqtsPiZkdmzLMkZg5Fwnpy`.

Terceiro hotfix: usuario pediu voltar a digitar senha na criacao. Fluxo principal agora e `Digitar senha agora` com confirmacao; convite por e-mail e senha provisoria permanecem opcoes explicitas. Diagnostico do reset por e-mail mostrou SendGrid retornando `Maximum credits exceeded`, entao o codigo classifica `sendgrid_credits_exceeded`, mas envio real depende de liberar creditos/cota ou trocar a chave SendGrid. Validacao: backend 68 passed, frontend focado 12 passed, Spec Kit/lint/build OK. Publicado com Railway `cceb5114-87db-46fe-a66b-55529288b5c6` e Vercel `dpl_ApJKS56pBcAo2XK1f2fCBPJYHZbe`.

Quarto hotfix: aba `/tasks` > `Onboarding` falhava no piloto porque o scoreboard recalculava score de 91 alunos em tempo real. O endpoint agora retorna snapshot persistido por query direta, mantendo recalculo apenas no detalhe do aluno selecionado. Diagnostico com banco do piloto caiu para 91 snapshots em 0.255s. Validacao: Spec Kit OK e backend focado 11 passed. Publicado com Railway `ca848b6a-6467-47a3-909f-1e34cae8b410`; smoke autenticado do endpoint publicado retornou 91 itens.

Quinto hotfix: Central Cordex permitia clicar `Concluir`/outcomes em recomendacao IA antes de `Comecar execucao`, gerando erro de aprovacao no canto da tela. A UI agora desabilita esses outcomes ate `awaiting_outcome` e explica que a execucao precisa ser iniciada primeiro. Validacao: teste focado da inbox IA 7 passed, lint/build OK e Spec Kit OK. Publicado com Vercel `dpl_AEWyBRFvPfppoQQbaxfT6ziHziSx`; smoke em `/tasks` e asset publicado OK.

## 2026-05-21 - Cordex Command Center Frontend V2
Cordex Command Center passa a ser o padrao visual premium do produto. A fase 09.6 entrega design system, app shell e dashboards principais em ondas, preservando fluxos operacionais e contratos existentes.

## 2026-05-20 - Kommo como canal universal das automacoes
Kommo ja existe como canal real em Work Queue, bioimpedancia e envios manuais. A fase 09.4 passa a tratar Kommo como canal principal tambem para automacoes, evitando que regras antigas escapem para WhatsApp/e-mail sem passar pelo roteador.

## 2026-05-15 - Kommo Salesbot Outbound
Cordex esta evoluindo a Kommo de handoff operacional para canal real de envio supervisionado. A rota principal passa a ser Salesbot por dominio, com handoff antigo como fallback.

## 2026-05-15 - Kommo PDF Nativo
Bioimpedancia e outros relatorios com arquivo passam a mirar upload nativo na Files API da Kommo. Link temporario segue disponivel apenas como fallback operacional.

## 2026-05-19 - Cordex Copy Agent
Retencao, onboarding e tasks passam a ter rascunhos de mensagem por agente especialista quando seguro. Templates fixos continuam fallback e nenhum envio automatico foi ativado.

## 2026-05-20 - Quality Hardening 09.5
Antes de avancar novas features, a base tecnica passa por endurecimento: Alembic sem branch redundante, CI menos permissivo, `OPENAI_SPECIALIST_MODEL` corrigido para modelo valido e fragilidade do Actuar Bridge tratada como risco monitorado.
