# Ruflo Adoption Notes

## Status

Ruflo foi baixado localmente em `C:\aigymos\external\ruflo` para estudo e referencia arquitetural.

Fonte: `https://github.com/ruvnet/ruflo`

Commit analisado: `c37b7764b chore(plugin): bump neural-trader pin 2.7.2 -> ^2.7.6 (#1982)`

Licenca: MIT. Qualquer reutilizacao direta de codigo deve preservar a nota de copyright/licenca.

## Decisao De Escopo

Ruflo sera usado para o desenvolvimento do Cordex Gym OS, nao como feature do sistema para academias.

Ele deve apoiar engenharia, coordenacao de agentes, revisao, testes, safety e memoria de desenvolvimento. Ele nao deve aparecer na UI, nos planos comerciais, nas automacoes de academia ou no runtime do SaaS.

## Cuidado de Integracao

Ruflo nao deve ser copiado integralmente para o runtime do Cordex Gym OS neste momento.

Motivos:

- O projeto e uma plataforma de orquestracao de agentes para Claude Code/CLI/MCP, nao uma dependencia pequena de runtime para FastAPI.
- O clone em Windows gerou colisao de arquivos por diferenca de maiusculas/minusculas em `.agents/skills/.../SKILL.md` e `skill.md`.
- O Cordex Gym OS ja possui GSD, Spec Kit, Obsidian, Autopilot, Work Queue, TaskEvent, AI Review Center e agentes por dominio. Integrar Ruflo inteiro como produto duplicaria conceitos.
- A incorporacao correta e usar Ruflo como camada de engenharia por fora do produto.

## Funcionalidades Ruflo Mais Uteis Para O Cordex Gym OS

### 1. Swarm / Coordenacao de agentes

Referencia Ruflo: `plugins/ruflo-swarm`.

O que aproveitar:

- Topologias de agentes com papeis claros.
- Worktree isolation por agente.
- Coordenador hierarquico para evitar drift.
- Limites de 6 a 8 agentes para trabalhos de codigo.

Aplicacao no Cordex Gym OS:

- Usar como inspiracao para evoluir nossa execucao GSD em fases grandes.
- Separar agentes internos por dominio: backend, frontend, testes, seguranca, produto e deploy.

### 2. Workflows com estado

Referencia Ruflo: `plugins/ruflo-workflows`.

O que aproveitar:

- Estado `created -> running -> paused -> completed/cancelled`.
- Gates de aprovacao humana.
- Templates reutilizaveis.

Aplicacao no Cordex Gym OS:

- Fortalecer `AutomationJourney` com uma maquina de estados mais explicita.
- Usar gates humanos em jornadas sensiveis: financeiro, cancelamento, lesao, reclamacao.

### 3. Autopilot com aprendizado

Referencia Ruflo: `plugins/ruflo-autopilot`.

O que aproveitar:

- Loop de progresso, historico e predicao da proxima acao.
- Aprendizado de padroes a partir de tarefas concluidas.

Aplicacao no Cordex Gym OS:

- Evoluir `Task Autopilot` para aprender quais outcomes funcionam por dominio.
- Priorizar templates e playbooks com maior taxa de resposta/recuperacao.

### 4. Memoria vetorial / AgentDB

Referencia Ruflo: `plugins/ruflo-agentdb`.

O que aproveitar:

- Namespace por finalidade.
- Memoria episodica, semantica e padroes de sucesso.
- Convencao de nomes para evitar colisao.

Aplicacao no Cordex Gym OS:

- Criar memoria operacional por academia, sem misturar tenants.
- Namespaces sugeridos:
  - `gym-{id}-retention-patterns`
  - `gym-{id}-kommo-drafts`
  - `gym-{id}-assessment-insights`
  - `gym-{id}-task-outcomes`

### 5. AIDefence / Guardrails

Referencia Ruflo: `plugins/ruflo-aidefence`.

O que aproveitar:

- Padrao de 3 gates: PII antes de armazenar, sanitizacao, prompt-injection antes de LLM.
- Quarentena de conteudo suspeito.

Aplicacao no Cordex Gym OS:

- Fortalecer guardrails do Agente IA Kommo, Personal IA, Aluno IA e Video IA.
- Bloquear prompt injection vindo de mensagens de alunos/leads antes de entrar em prompts especialistas.

### 6. Testgen / Gaps de teste

Referencia Ruflo: `plugins/ruflo-testgen`.

O que aproveitar:

- Worker de lacunas de cobertura.
- Sugestao de testes por arquivo alterado.
- Gate de refinamento com cobertura minima.

Aplicacao no Cordex Gym OS:

- Criar checklist automatizado pos-fase:
  - arquivos alterados sem teste correspondente;
  - endpoints novos sem teste de permissao;
  - services novos sem teste multi-tenant.

### 7. Cost Tracker

Referencia Ruflo: `plugins/ruflo-cost-tracker`.

O que aproveitar:

- Custo por agente, modelo, tarefa e periodo.
- Alertas por orcamento.
- Recomendacao de downgrade de modelo.

Aplicacao no Cordex Gym OS:

- Medir custo real por modulo de IA:
  - Bioimpedancia IA;
  - Agente Kommo;
  - Personal IA;
  - Aluno IA;
  - Video IA;
  - AI Review Center.

### 8. Browser Sessions

Referencia Ruflo: `plugins/ruflo-browser`.

O que aproveitar:

- Sessao de browser como artefato auditavel.
- Screenshots, trajetoria, snapshots e findings.

Aplicacao no Cordex Gym OS:

- Usar em validacao de piloto:
  - login por papel;
  - fluxo de tasks;
  - configuracao Kommo;
  - salvar avaliacao;
  - gerar PDF;
  - importar agenda de avaliacoes.

## O Que Nao Incorporar Agora

- MCP server completo Ruflo no runtime do Cordex Gym OS.
- Dependencias alpha de `@claude-flow/*` em producao.
- Federation entre agentes em maquinas diferentes.
- Agentes autonomos com permissao de escrita sem revisao.
- Memoria de agentes sem isolamento por tenant.
- Autoenvio de mensagens baseado apenas em LLM.

## Roadmap Sugerido

### Curto prazo

- Usar este documento como referencia de arquitetura.
- Criar backlog de "AI Ops Governance" baseado em Ruflo: custo, safety, test gaps e browser verification.
- Fortalecer guardrails dos agentes com padrao de 3 gates.

### Medio prazo

- Criar metricas de custo por modulo de IA.
- Criar detector de lacunas de teste por fase GSD.
- Criar browser verification para fluxos criticos do piloto.

### Longo prazo

- Evoluir o Cordex Gym OS para memoria operacional por academia.
- Usar aprendizado de outcomes para melhorar Autopilot e jornadas.
- Criar orquestracao de agentes internos para desenvolvimento assistido, sem virar dependencia de runtime.

## Decisao

Ruflo entra como referencia e fonte de padroes para o AI First OS, nao como substituicao da arquitetura atual.

Principio: incorporar as ideias que reduzem risco operacional, melhoram seguranca, aumentam auditabilidade e reduzem custo de IA, mantendo o Cordex Gym OS simples o suficiente para operar no piloto.
