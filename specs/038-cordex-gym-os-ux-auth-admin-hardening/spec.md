# Spec 038 - Cordex Gym OS UX/Auth/Admin Hardening

## User Story
Como operador ou gestor do Cordex Gym OS, quero uma interface menos poluida, reset de senha acessivel e criacao de usuarios mais simples para operar o piloto sem friccao ou promessas falsas.

## Requirements
- O trabalho deve usar GSD e Spec Kit sem alterar a fase 037 do agente WhatsApp.
- A limpeza visual deve ser conservadora no app inteiro: remover ruido, decoracao e CTAs/status hardcoded sem apagar rotas ou modulos.
- App shell, dashboards e configuracoes devem manter RBAC, navegacao, logout, notificacoes e dados reais.
- O login deve expor fluxo de "esqueci minha senha" com e-mail e slug da academia.
- O reset por e-mail deve usar o resultado real do provedor de envio e nao persistir token quando o envio falhar.
- O fluxo de reset deve continuar sem enumerar contas inexistentes.
- Usuarios autenticados devem conseguir alterar a propria senha em Configuracoes > Seguranca quando o provedor de e-mail estiver indisponivel.
- A tela de usuarios deve permitir criar usuario com nome, e-mail, papel e senha digitada pelo administrador como fluxo principal.
- Convite por e-mail e senha provisoria auto-gerada devem existir apenas como opcoes explicitas na criacao ou no reset administrativo.
- Campos de cargo, turno, escopo de turno e avatar devem ficar como opcoes avancadas na criacao.
- A senha provisoria gerada deve aparecer apenas uma vez na resposta imediata/UI e nunca em logs de auditoria.
- Owner e manager devem poder resetar senha da equipe dentro das regras de RBAC.

## Non-Goals
- Remover rotas ou modulos existentes.
- Introduzir `must_change_password` nesta V1.
- Publicar automaticamente em Vercel/Railway.
- Refazer profundamente todas as paginas operacionais.

## Acceptance Criteria
- `specify check` passa antes e depois da implementacao.
- Login publicado tem entrada clara para recuperacao de senha.
- `/reset-password#token=...` continua funcionando e coberto por teste.
- `POST /api/v1/auth/forgot-password` diferencia falha operacional de e-mail de usuario inexistente sem enumerar contas.
- `POST /api/v1/users/me/password` valida senha atual, troca a senha, invalida tokens antigos e nao registra segredo em auditoria.
- `POST /api/v1/users/` usa senha manual como padrao, aceita convite quando `password_setup=invite` e so gera senha provisoria quando `password_setup=temporary`.
- `POST /api/v1/users/{user_id}/password-reset` aplica RBAC, invalida sessoes do alvo e retorna senha provisoria uma unica vez.
- `UsersPage` mostra campos de senha inicial como padrao e painel copiavel apenas quando senha provisoria foi solicitada.
- App shell/configuracoes/dashboards ficam menos ruidosos sem perder acesso a rotas existentes.
- Testes focados de backend e frontend passam.
