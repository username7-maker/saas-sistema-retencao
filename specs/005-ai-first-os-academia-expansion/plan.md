# Implementation Plan: AI-First OS Academia Expansion v2

**Branch**: `005-ai-first-os-academia-expansion` | **Date**: 2026-04-24 | **Spec**: [spec.md](./spec.md)

## Executive summary

O HTML `ai_first_os_academia_v2.html` amplia a visao original. A versao anterior cabia em oito blocos; a v2 organiza o produto em cinco camadas e dezoito modulos:

- **Aquisicao & funil pre-lead**
  - Captacao de Leads
  - Marketing IA
  - Compliance LGPD
- **Core aluno & treino**
  - AI Coach Pessoal
  - Nutricao & Dieta
  - Avaliacao Fisica IA
  - Agendamento Smart
  - Aulas Online / Hibridas
  - Gestao de Alunos / CRM
- **Gestao operacional & financeira**
  - Gestao Financeira
  - Analytics & BI
  - Gestao de Equipe
  - Estoque & Loja
- **Engajamento, expansao & compliance**
  - Gamificacao & Comunidade
  - Multi-unidades & Franquia
  - App White Label
  - Integracoes & IoT
- **Infraestrutura & dados**
  - Motor de IA Central
  - Dados & Seguranca

O programa continua viavel, mas agora precisa de quatro releases, nao tres. A primeira fase permanece `7.0`, porem o nome correto passa a ser `Lead-to-member intelligence graph e payload canonico`.

## Current baseline

### O que o produto ja tem parcialmente

- Members/Profile 360
- CRM e funil comercial basico
- Avaliacoes, bioimpedancia, laudos premium e relatorios tecnicos
- Tasks operacional + onboarding
- Retention dashboard e AI Inbox
- Dashboards executive/operational/commercial/financial/retention
- Reports premium e board packs
- WhatsApp real, Kommo parcial, Actuar validado
- LGPD baseline, tenant guardrails, jobs duraveis e auditabilidade

### O que a v2 adiciona ou reforca

- pre-lead real: captacao, landing, aula experimental, chatbot e score de propensao
- compliance operacional visivel: contratos, consentimentos, termos e vencimentos
- avaliacao fisica IA alem da bioimpedancia atual
- gestao financeira com DRE, caixa, contas e inadimplencia
- gestao de equipe com escala, comissao, performance e NPS por professor
- estoque/loja/PDV
- gamificacao e comunidade
- multiunidade/franquia
- app white label
- aulas online/hibridas
- plataforma conectada: IoT, pagamentos, catraca, wearables, equipamentos e API aberta

## Non-negotiable sequencing

### Gate 0 - antes de abrir a expansao

- `4.43.1` ja foi validada e nao bloqueia mais o milestone novo
- Spec Kit, GSD e Obsidian devem permanecer alinhados
- o primeiro modulo novo precisa reforcar a verdade operacional, nao criar um super-modulo paralelo

### Gate 1 - antes de app/aluno/coach direto

- grafo lead-to-member funcionando
- consentimentos e origem de lead preservados
- workspace staff-first validado por professor
- side effects seguros para tarefa, mensagem, follow-up e owner

### Gate 2 - antes de financeiro/equipe/estoque amplo

- fonte real de receita/planos/inadimplencia definida
- diferenca entre role, cargo, escala e comissao resolvida
- modelo de produto/estoque/venda definido

### Gate 3 - antes de IoT, app white label e multiunidade

- estrategia de app/mobile decidida
- contratos de integracao e degraded states padronizados
- modelo de unidade/franquia definido sem quebrar multi-tenant

## Release plan

## Release A - v3.3.0 AI Lead-to-Member Intelligence Foundation

### Objetivo

Transformar o produto de `Retention OS com AI Inbox` para `Lead-to-Member Intelligence OS`, ainda 100% staff-first.

### Workstreams

#### A1. Lead-to-Member Intelligence Graph

- unificar sinais de:
  - captacao/pre-lead
  - CRM
  - consentimentos
  - onboarding
  - check-ins
  - avaliacoes e bioimpedancia
  - tasks
  - risco
  - renovacao/upsell
- criar payload canonico para:
  - Profile 360
  - AI Inbox
  - CRM/growth
  - dashboards
  - reports

#### A2. Lifecycle Orchestration

- segmentacao comportamental automatica
- jornada alem do D30
- roteamento por turno, papel e owner
- estados de aquisicao, onboarding, ativo, risco, renovacao e reativacao

#### A3. Assessment + Coach Workspace Foundation

- staff-first coach workspace
- progresso, PRs, aderencia e sinais de estagnacao
- avaliacao fisica IA como estrutura futura
- bioimpedancia e laudos premium como base ja real
- override humano obrigatorio

#### A4. BI Foundation Upgrade

- cohort
- LTV
- forecast
- receita em risco
- impacto de onboarding, retencao e follow-up
- weekly digest gerencial

### Resultado esperado

- `Gestao de Alunos` e `Analytics & BI` ficam muito mais proximos do HTML v2
- `Avaliacao Fisica IA` nasce de forma honesta sobre dados reais
- `AI Coach Pessoal` comeca como workspace de professor, nao como app magico para aluno

## Release B - v3.4.0 Acquisition, Compliance and Revenue OS

### Objetivo

Expandir o sistema para aquisicao pre-lead, compliance operacional, marketing assistido e financeiro gerencial.

### Workstreams

#### B1. Acquisition OS

- pagina de captura
- aula experimental agendavel
- origem/canal/campanha
- chatbot qualificador
- score de propensao
- handoff para CRM

#### B2. Compliance OS

- contratos digitais
- consentimento LGPD
- consentimento de imagem
- termos por plano/canal
- historico auditavel de aceites
- vencimento de termos

#### B3. Growth / Marketing OS

- audiences de conversao, renovacao, reativacao e upsell
- WhatsApp/email com aprovacao humana
- copy assistida por comportamento
- experimentacao simples
- Kommo/CRM como handoff oficial quando aplicavel

#### B4. Finance Foundation

- caixa diario
- contas a pagar/receber
- inadimplencia
- receita em risco
- DRE basico
- forecast de fluxo de caixa quando houver dados

### Resultado esperado

- `Captacao de Leads`, `Compliance LGPD`, `Marketing IA` e parte de `Gestao Financeira` entram como produto operacional.

## Release C - v3.5.0 Adherence, Scheduling and Staff Operations

### Objetivo

Expandir aderencia fora do treino, agenda, equipe, aulas hibridas e operacao de loja.

### Workstreams

#### C1. Nutrition OS

- metas nutricionais por objetivo
- plano alimentar estruturado
- registro de aderencia
- foto de refeicao somente com revisao/degraded state
- suplementacao assistida, nao automatica

#### C2. Smart Scheduling

- reservas e agenda de aulas
- ocupacao por horario
- previsao de pico
- sugestao de horario por perfil
- fila de espera
- cancelamento/reagendamento

#### C3. Online / Hybrid Classes

- biblioteca de videos
- transmissao ao vivo quando houver provider
- planos hibridos
- progressao e engajamento fora da academia

#### C4. Staff Management

- escala
- responsabilidades
- ponto/registro operacional quando definido
- comissoes quando houver modelo
- performance por professor
- NPS por professor

#### C5. Stock & Store

- produtos
- estoque
- reposicao
- vendas
- comissao de venda
- PDV/app somente quando houver contrato real

### Resultado esperado

- `Nutricao & Dieta`, `Agendamento Smart`, `Aulas Online`, `Gestao de Equipe` e `Estoque & Loja` deixam de ser visao e viram modulos faseados.

## Release D - v3.6.0 Student Companion and Connected Network

### Objetivo

Abrir experiencias diretas ao aluno, comunidade, app white label, multiunidade e plataforma conectada.

### Workstreams

#### D1. Student Companion + App White Label

- app/web companion do aluno
- metas, progresso, agenda e mensagens
- push notifications
- check-in e acesso via app quando houver integracao
- coach conversacional somente depois de staff-first validado

#### D2. Gamification & Community

- desafios
- ranking
- badges
- grupos por objetivo
- feed de progresso quando houver politica de privacidade clara
- integracao com comunidades WhatsApp quando seguro

#### D3. Multi-units & Franchise

- painel consolidado
- benchmarking entre unidades
- autonomia por unidade
- padronizacao de onboarding
- royalties/financeiro de franquia quando houver modelo

#### D4. Connected Gym

- wearables
- smart equipment
- catraca/acesso
- pagamentos
- open API
- voz/visao computacional somente com pipeline validado

#### D5. Data & AI Platform

- data warehouse multi-tenant
- vector store quando houver caso real
- motor de recomendacao compartilhado
- backup e auditoria ampliados
- learning loops com governanca

### Resultado esperado

- `App White Label`, `Gamificacao`, `Multi-unidades`, `Integracoes & IoT`, `Motor de IA Central` e `Dados & Seguranca` entram como plataforma conectada posterior.

## Mapping from HTML v2 to releases

| HTML v2 module | Estado atual | Release alvo | Observacao |
| --- | --- | --- | --- |
| Captacao de Leads | parcial via CRM/public flows | v3.4.0 | precisa pre-lead e consentimento |
| Marketing IA | parcial | v3.4.0 | sobre CRM/WhatsApp/Kommo/AI Inbox |
| Compliance LGPD | baseline forte, UX operacional parcial | v3.4.0 | contratos/termos/aceites visiveis |
| AI Coach Pessoal | ausente como produto fechado | v3.3.0 -> v3.6.0 | staff-first primeiro, aluno depois |
| Nutricao & Dieta | ausente | v3.5.0 | assistivo, sem foto automatica falsa |
| Avaliacao Fisica IA | parcial via avaliacoes/bioimpedancia | v3.3.0 | posture/vision depois |
| Agendamento Smart | ausente | v3.5.0 | depende de agenda/capacidade |
| Aulas Online/Hibridas | ausente | v3.5.0 | depende de media/provider |
| Gestao de Alunos/CRM | forte parcial | v3.3.0 | primeiro grande alvo |
| Gestao Financeira | parcial em dashboards | v3.4.0 | precisa fontes financeiras |
| Analytics & BI | parcial forte | v3.3.0 -> v3.4.0 | cohort/LTV/forecast |
| Gestao de Equipe | parcial por usuarios/tasks | v3.5.0 | separar cargo/role/escala |
| Estoque & Loja | ausente | v3.5.0 | modulo operacional posterior |
| Gamificacao & Comunidade | ausente | v3.6.0 | depois de app/comunidade |
| Multi-unidades & Franquia | ausente | v3.6.0 | sobre multi-tenant, nao antes |
| App White Label | ausente | v3.6.0 | posterior ao staff-first |
| Integracoes & IoT | ausente/parcial | v3.6.0 | ultima camada |
| Motor de IA Central | parcial | v3.3.0 -> v3.6.0 | substrate incremental |
| Dados & Seguranca | baseline forte | v3.3.0 -> v3.6.0 | reforco continuo |

## Candidate GSD phasing

### v3.3.0 AI Lead-to-Member Intelligence Foundation

1. `7.0` Lead-to-member intelligence graph e payload canonico
2. `7.1` Lifecycle orchestration e gestao de alunos expandida
3. `7.2` Assessment + coach workspace foundation
4. `7.3` BI foundation upgrade

### v3.4.0 Acquisition, Compliance and Revenue OS

5. `8.0` Acquisition OS e pre-lead intelligence
6. `8.1` Compliance OS: contratos, termos e consentimentos
7. `8.2` Growth / marketing OS
8. `8.3` Finance foundation

### v3.5.0 Adherence, Scheduling and Staff Operations

9. `9.0` Nutrition OS
10. `9.1` Smart scheduling
11. `9.2` Online / hybrid classes
12. `9.3` Staff management
13. `9.4` Stock & store

### v3.6.0 Student Companion and Connected Network

14. `10.0` Student companion + app white label
15. `10.1` Gamification & community
16. `10.2` Multi-units & franchise
17. `10.3` Connected gym: IoT, access, payments and API
18. `10.4` Data & AI platform advanced modalities

## Risks and decisions

### Risks

- abrir app/coach para aluno antes da base staff-first
- ativar compliance/marketing sem consentimento rastreavel
- criar financeiro/equipe/estoque sem fonte real e virar planilha paralela
- vender multiunidade antes de resolver modelo de unidade/franquia
- mostrar IoT, visao, voz ou nutricao por foto como capacidade ativa sem provider

### Decisions locked

- a primeira fase permanece `7.0`, mas agora com escopo `lead-to-member`
- o HTML v2 nao sera implementado como big bang
- app do aluno, IoT e multiunidade ficam para release posterior
- qualquer recomendacao de impacto continua com revisao humana
- degraded/manual state e obrigatorio para capacidades sem integracao real

## Verification strategy

- cada release deve fechar pelo menos um modulo do HTML v2 em estado real de uso
- nenhuma capacidade aparece como ativa sem fonte real, provider, consentimento ou fluxo manual explicito
- cada fase nova deve manter:
  - Spec Kit atualizado
  - GSD atualizado
  - Obsidian atualizado
  - testes focados
  - evidencia de piloto quando houver side effects

## Recommended next step

Abrir `7.0 Lead-to-member intelligence graph e payload canonico`.

O primeiro planejamento tecnico deve mapear:

- entidades atuais que entram no grafo
- lacunas de dados para pre-lead e consentimento
- payload canonico inicial
- superficies consumidoras iniciais: Profile 360, AI Inbox, CRM e dashboards/reports
