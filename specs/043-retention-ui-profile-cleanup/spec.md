# Spec 043 - Retention UI Profile Cleanup

## User Story
Como operador da Cordex, quero que as telas de retencao organizem os sinais, recomendacoes e acoes de forma mais clara, para agir rapido sem perder contexto e sem encontrar cards ilegíveis no tema escuro.

## Requirements
- O trabalho deve seguir GSD, Spec Kit e registro Obsidian.
- O drawer de playbook da retencao deve transformar os sinais captados em uma leitura compacta e escaneavel.
- O drawer de playbook deve manter as informacoes existentes, mas organizar por resumo, sinais, copiloto, proxima acao, evidencias, mensagem sugerida e playbook.
- As acoes principais do drawer devem ficar sempre acessiveis em uma barra fixa: WhatsApp, Enviar Kommo, Abrir perfil 360 e Marcar resolvido quando permitido.
- As acoes extras existentes devem continuar disponiveis em uma area secundaria compacta.
- A aba Retencao do drawer de aluno deve usar tokens compativeis com dark mode, sem fundos claros que prejudiquem leitura.
- O Perfil 360 deve esconder temporariamente os blocos Cordex Coach e Video de Movimento apenas nessa pagina.
- Settings, endpoints, services, permissões e rotas globais de Coach/Motion nao devem ser removidos nesta V1.
- A inspiracao visual do Actuar deve ser aplicada apenas como organizacao mais objetiva de informacoes e acoes, sem copiar tema claro ou mudar a estrutura principal.

## Non-Goals
- Alterar APIs, banco, RBAC ou contratos de dados.
- Remover definitivamente Cordex Coach ou Video de Movimento do produto.
- Redesenhar o app shell, dashboards ou settings nesta fase.
- Publicar no piloto antes de validacao local.

## Acceptance Criteria
- `specify check` passa antes e depois.
- Drawer de retencao renderiza sinais compactos e a barra fixa de acoes.
- As acoes principais continuam funcionando com os mesmos handlers existentes.
- Aba Retencao do drawer de aluno nao usa cards claros ilegíveis no tema escuro.
- Perfil 360 nao renderiza Cordex Coach nem Video de Movimento.
- Testes focados de retencao e Perfil 360 passam.
- `npm run lint` e `npm run build` passam.
