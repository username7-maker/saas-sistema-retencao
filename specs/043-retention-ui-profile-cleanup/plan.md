# Plan 043 - Retention UI Profile Cleanup

## Frontend
- Reorganizar `RetentionDashboardPage` para reduzir rolagem e deixar os principais comandos sempre visiveis no drawer de playbook.
- Compactar os sinais captados em cards menores, mantendo as barras e a semantica de risco.
- Dividir o conteudo do copiloto/playbook em blocos de leitura rapida: contexto, sinais, playbook, mensagem e acoes.
- Corrigir `MemberDetailDrawer` para usar apenas superficies dark-safe na aba Retencao.
- Remover do render do Perfil 360 os paineis Cordex Coach e Video de Movimento, limpando imports e codigo morto local quando aplicavel.

## Verification
- Atualizar testes focados em `RetentionDashboardPage` e `MemberProfile360Page`.
- Adicionar cobertura do drawer de aluno se necessario para garantir que a aba Retencao segue renderizando.
- Rodar `specify check`, testes focados, lint e build.

## Rollout
- Sem migration e sem alteracao de API.
- Publicacao no piloto somente apos validacao local e revisao do resultado visual.
