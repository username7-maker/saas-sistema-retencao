# EMPRESA.md — invariantes do projeto

> Regras **não-negociáveis** deste projeto. Todo agente lê antes de trabalhar.
> Este repositório é a **base oficial do Cordex Gym OS** (decisão do fundador em 2026-07-08).

## O que é

**Cordex Gym OS** é o primeiro produto da **Cordex** — SaaS B2B AI-first que funciona como
camada operacional e de receita para negócios locais. Feito para academias (800–1.500
alunos), com a **ProGym** como cliente fundadora: BI, CRM, retenção preditiva, NPS,
avaliação física, WhatsApp e compliance LGPD. Transforma dados soltos da operação em
ações práticas para a equipe — quem precisa de ação, qual o próximo passo, se foi
executado e o que rendeu. A Cordex expande depois para clínicas, estética, escolas e
outros negócios com atendimento, vendas, recorrência e retenção.

## Invariantes (7, não-negociáveis)

1. **Multi-tenant desde sempre** — toda entidade, query, job e log carrega `gym_id`.
   **Nada é hard-coded pra ProGym** (o slug `progym` só existe como dado, nunca como
   regra). "Academia" é a primeira vertical da Cordex, não a única.
2. **Ação em vez de dashboard** — todo insight vira **tarefa com dono, prazo e status**.
   O sistema mede execução (foi feito?) e resultado (o que rendeu?). Feature que só exibe
   dado sem gerar ação acompanhável está incompleta.
3. **Integrações trocáveis** — WhatsApp, e-mail (SendGrid), LLM (Claude): consumidor
   nunca chama o vendor direto; sempre pela camada de serviço/adapter em
   `app/services`/`app/utils`. Trocar vendor = novo adapter, zero refactor nos routers.
4. **IA sugere, humano aprova** — nenhuma mensagem sai para aluno/lead sem regra ou
   aprovação explícita da academia. Toda sugestão da IA é auditável (registra o porquê) e
   output de LLM é validado por schema antes de qualquer efeito.
5. **Dados de aluno são sagrados (LGPD)** — CPF criptografado (AES-256), auditoria de
   ações sensíveis, exportação e anonimização preservadas em qualquer refactor. Dados
   pessoais nunca em log e nunca em prompt de LLM sem necessidade real.
6. **Contratos validados nas fronteiras** — Pydantic em todo endpoint/job/webhook no
   backend; TypeScript estrito no frontend consumindo os mesmos contratos. Tipos derivam
   dos schemas, nunca o contrário.
7. **Segurança baseline** — JWT curto (15 min) + refresh (7 dias), RBAC por papel,
   bcrypt 12 rounds, rate limit no WhatsApp e endpoints públicos, CORS whitelist
   explícita, HTTPS only em produção, secrets fora do código (`.env` gitignored).

## Stack (a real deste produto — não mude sem ADR)

- **Backend:** Python 3.11 + FastAPI + SQLAlchemy 2.0 + Alembic + APScheduler
- **Banco:** PostgreSQL via Supabase
- **Frontend:** React 18 + TypeScript + Vite + Tailwind + React Query + Recharts
- **IA:** Anthropic Claude (`CLAUDE_API_KEY` / `CLAUDE_MODEL`)
- **Mensageria:** WhatsApp API (com rate limit/hora) + SendGrid (e-mail)
- **Deploy:** Supabase + Railway (API/worker/Redis) + Vercel (front), CI no GitHub Actions

> **Nota de método:** o STACK-DEFAULT da Accelera360 (TypeScript/Fastify/Next) NÃO se
> aplica aqui — desvio aceito pela regra "produto existente em produção/piloto"
> (justificativa mais forte que existe). O time trabalha na stack acima. Smoke do time:
> ver `.ai-team.json`.

## Design

Contexto de produto e visual vive em `PRODUCT.md` e `DESIGN.md` (raiz do repo) —
gerados pelo skill `/impeccable`. North Star: **"The Quiet Nucleus"** (navy quase-preto
+ um único acento azul `#3B82F6`, ancorado na logo da Cordex). Todo agente que mexer em
UI deve ler `DESIGN.md` antes; ele já carrega os Don'ts que vêm dos invariantes acima
(ação em vez de dashboard, sinal em vez de ruído).

## Como o time trabalha aqui

- Método multi-agente: `specs/PARALLEL-PROTOCOL.md` (papéis, slots, zoning, worktrees).
- Snapshot vivo do projeto: `specs/RESUME.md`.
- Specs de produto já existentes: `specs/NNN-*/` (numeração preservada — continue dela).
- Todo erro corrigido vira aprendizado registrado (LEARNINGS) — o ciclo não rompe.
