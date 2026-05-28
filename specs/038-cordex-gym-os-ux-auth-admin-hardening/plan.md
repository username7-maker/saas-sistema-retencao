# Plan 038 - Cordex Gym OS UX/Auth/Admin Hardening

## Technical Plan
1. Registrar fase GSD 09.8 e apontar `.specify/feature.json` para esta spec.
2. Ajustar backend de reset para usar `send_email_result`, persistir token somente apos envio confirmado e manter resposta generica para contas inexistentes.
3. Adicionar contratos administrativos para criacao com senha provisoria gerada e reset de senha por usuario alvo.
4. Atualizar frontend de login, settings e users para reduzir atrito e remover fluxo confuso de token manual.
5. Fazer limpeza visual conservadora no app shell, configuracoes e dashboard executivo removendo decoracao/CTAs/status sem base real.
6. Cobrir com testes focados e validacoes de build/lint.

## Risk Control
- Nao remover rotas, permissoes ou modulos.
- Nao gravar senha provisoria em audit logs.
- Nao alterar storage de sessao nem cookies.
- Nao transformar falha de usuario inexistente em sinal enumeravel.
- Manter a V1 sem migrations obrigatorias.
