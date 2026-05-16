# Ruflo Development Workflow

## Objetivo

Usar Ruflo para melhorar o desenvolvimento do Cordex Gym OS, nao como funcionalidade do produto.

Ruflo deve ajudar em:

- coordenacao de tarefas grandes;
- escolha do tipo de agente/trabalho;
- revisao de seguranca;
- deteccao de lacunas de teste;
- memoria de padroes de implementacao;
- validacao de fluxos com browser;
- controle de custo e complexidade de IA.

## Estado Atual

Ruflo esta clonado em:

`C:\aigymos\external\ruflo`

Observacoes tecnicas:

- O clone local nao roda diretamente sem build porque `dist/` nao esta presente.
- No Windows houve colisao de arquivos `SKILL.md`/`skill.md` em alguns plugins.
- O comando `npx ruflo@latest` demorou mais que 2 minutos nesta maquina; usar `npm.cmd`/`npx.cmd` em vez de `npm`/`npx` no PowerShell.

## Como Usar No Dia A Dia

### Antes De Uma Fase Grande

Use Ruflo como camada de roteamento:

1. Identificar se o trabalho e backend, frontend, IA, seguranca, testes, deploy ou produto.
2. Definir ownership por area.
3. Verificar riscos: tenant isolation, LGPD, webhooks, permissoes, dados sensiveis, envio automatico.
4. Confirmar quais testes devem existir antes de publicar.

### Durante A Implementacao

O fluxo principal continua:

1. GSD define a execucao.
2. Spec Kit define o contrato formal.
3. Obsidian registra decisoes.
4. Ruflo inspira coordenacao, test gaps, safety e memoria.

### Depois Da Implementacao

Ruflo deve orientar uma revisao de fechamento:

- Quais arquivos mudaram?
- Existe teste focado para cada service/router/componente novo?
- Algum endpoint novo ficou sem teste de permissao?
- Alguma automacao ou IA nova ficou sem guardrail?
- Algum prompt novo ficou sem versao/modelo/safety profile?
- Algum fluxo critico precisa de browser verification?

## Comandos Recomendados

No PowerShell, use `npx.cmd`, nao `npx`, para evitar bloqueio de execution policy.

```powershell
# Ver versao
npx.cmd ruflo@latest --version

# Inicializar para Codex, quando o pacote estiver respondendo
npx.cmd ruflo@latest init --codex

# Diagnostico
npx.cmd ruflo@latest doctor

# Roteamento de tarefa
npx.cmd ruflo@latest hooks route "implementar endpoint de tasks" --include-explanation

# Lacunas de teste
npx.cmd ruflo@latest hooks coverage-gaps --format table --limit 20
```

Tambem ha wrapper local:

```powershell
.\scripts\ruflo-dev.ps1 version
.\scripts\ruflo-dev.ps1 doctor
.\scripts\ruflo-dev.ps1 route "corrigir bug na Work Queue"
.\scripts\ruflo-dev.ps1 testgaps
```

## Onde Ruflo Encaixa No Nosso Processo

### GSD

Ruflo pode ajudar a decompor tarefas e sugerir papeis, mas a fase GSD continua sendo a fonte da execucao.

### Spec Kit

Ruflo pode sugerir lacunas de aceite e teste, mas a spec formal deve continuar em `specs/`.

### Obsidian / Planning Memory

Ruflo pode sugerir aprendizados e decisoes recorrentes. Decisoes duraveis devem ser registradas nos arquivos de memoria existentes.

## Usos Prioritarios Para O Cordex Gym OS

### 1. Test Gap Review

Rodar antes de publicar fases grandes para detectar:

- endpoint sem teste de auth;
- service sem teste multi-tenant;
- webhook sem teste de assinatura/token;
- IA sem teste de safety;
- migration sem teste de upgrade.

### 2. Security And AI Safety Review

Aplicar principalmente em:

- Kommo;
- WhatsApp;
- Autopilot;
- Personal IA;
- Aluno IA;
- Video IA;
- LGPD;
- financeiro.

### 3. Browser Verification

Usar para validar fluxos do piloto:

- login por papel;
- tarefas por perfil;
- salvar avaliacao;
- gerar relatorio PDF;
- importar agenda;
- configurar Kommo;
- revisar rascunho IA.

### 4. Development Memory

Guardar padroes que se repetem:

- como testar tenant isolation;
- como criar router FastAPI com roles;
- como criar outcome de task;
- como criar timeline operacional;
- como publicar piloto com Railway/Vercel.

## O Que Nao Fazer

- Nao adicionar Ruflo como dependencia de runtime do backend ou frontend.
- Nao gerar `.claude-flow` ou centenas de skills sem revisar impacto no repo.
- Nao deixar agentes modificarem arquivos de produto sem plano GSD.
- Nao usar agente autonomo para publicar deploy sem validacao humana.

## Proximo Passo Tecnico

Quando quisermos ativar Ruflo de fato nesta maquina:

1. Garantir que `npx.cmd ruflo@latest --version` responde.
2. Rodar `npx.cmd ruflo@latest init --codex` em uma branch separada.
3. Revisar arquivos gerados antes de commitar.
4. Confirmar se `AGENTS.md`, `.agents/skills` e MCP nao conflitam com Spec Kit.
5. Se estiver estavel, usar Ruflo em fases de desenvolvimento grandes.

