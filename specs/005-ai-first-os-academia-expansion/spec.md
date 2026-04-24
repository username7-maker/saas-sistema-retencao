# Feature Specification: AI-First OS Academia Expansion v2

**Feature Branch**: `005-ai-first-os-academia-expansion`  
**Created**: 2026-04-23  
**Updated**: 2026-04-24  
**Status**: Planned  
**Input**: User description: "Reavaliar `ai_first_os_academia_v2.html`, atualizar o que ja temos e criar o que precisar antes de abrir a fase 7.0."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operar o ciclo lead -> aluno -> retencao em uma verdade unica (Priority: P1)

Como owner ou manager da academia, eu quero que o sistema trate pre-lead, lead, aluno, onboarding, frequencia, avaliacao, risco e renovacao como um ciclo unico, para que recepcao, comercial, professores e gestao atuem sobre a mesma historia operacional.

**Why this priority**: A v2 do HTML adiciona `Captacao de Leads` e `Compliance LGPD` antes do aluno. Isso muda a fundacao: o primeiro grafo nao pode comecar apenas no membro; ele precisa preservar origem, consentimentos e handoff comercial.

**Independent Test**: Pode ser validado quando um contato que nasceu como lead tiver origem, consentimento, etapa comercial, conversao, onboarding, frequencia, avaliacoes e risco consumidos por Profile 360, AI Inbox e dashboards sem duplicacao de estado.

**Acceptance Scenarios**:

1. **Given** um lead captado por canal digital, **When** ele vira aluno, **Then** o sistema preserva origem, consentimentos, historico comercial e estado de onboarding no mesmo contexto canonico.
2. **Given** um aluno convertido com sinais de ausencia, baixa aderencia ou renovacao, **When** a AI Inbox ou o CRM abre sua proxima acao, **Then** a recomendacao usa o contexto de lead + aluno + relacionamento.

---

### User Story 2 - Dar ao professor um workspace de coach staff-first (Priority: P1)

Como professor, eu quero acompanhar progresso, avaliacoes, bioimpedancia, plano, aderencia e sinais tecnicos do aluno em um workspace unico, para ajustar treino com apoio da IA sem perder a decisao humana.

**Why this priority**: `AI Coach Pessoal` e `Avaliacao Fisica IA` sao centrais no HTML v2. No produto real, devem nascer como ferramenta para professor antes de qualquer coach direto para aluno.

**Independent Test**: Pode ser validado quando o professor consegue abrir o contexto do aluno, ver evolucao fisica/treino/aderencia e aplicar uma recomendacao assistida com override humano auditavel.

**Acceptance Scenarios**:

1. **Given** um aluno com avaliacoes e historico de treino, **When** o professor abre o workspace tecnico, **Then** ve progresso, gargalos, sinais de estagnacao e sugestao de proxima acao.
2. **Given** uma recomendacao de ajuste de plano, **When** o professor confirma, altera ou rejeita, **Then** a decisao humana fica registrada e o sistema nao executa sozinho.

---

### User Story 3 - Amadurecer BI, financeiro e gestao de equipe sobre dados reais (Priority: P1)

Como gerente, eu quero enxergar receita, risco, inadimplencia, equipe, produtividade e resultado operacional com indicadores consistentes, para tomar decisoes semanais sem montar planilhas paralelas.

**Why this priority**: A v2 adiciona `Gestao Financeira`, `Gestao de Equipe`, `Estoque & Loja` e reforca `Analytics & BI`. Parte do BI ja existe; financeiro/equipe/estoque precisam entrar de forma faseada e honesta.

**Independent Test**: Pode ser validado quando dashboards e reports mostrarem cohort, LTV, receita em risco, inadimplencia, execucao de equipe e sinais de margem sem depender de dados inventados.

**Acceptance Scenarios**:

1. **Given** uma academia com base de alunos e faturamento, **When** a gestao abre os dashboards, **Then** ve cohort, forecast, receita em risco e inadimplencia com origem rastreavel.
2. **Given** professores e recepcao usando tarefas, avaliacoes e follow-ups, **When** a gerencia revisa performance, **Then** o sistema mostra execucao operacional por pessoa, turno e responsabilidade.

---

### User Story 4 - Expandir growth, comunidade e canais sem automacao falsa (Priority: P2)

Como equipe comercial/gestao, eu quero operar campanhas, reativacao, upsell, comunidade e comunicacao a partir do comportamento real de leads e alunos, para aumentar conversao e retencao sem disparos cegos.

**Why this priority**: A v2 conecta `Marketing IA`, `Captacao de Leads`, `Gamificacao & Comunidade`, `App White Label` e canais como WhatsApp/chatbot. Isso depende do grafo canonico, de consentimento e de side effects auditaveis.

**Independent Test**: Pode ser validado quando o sistema cria audiencias acionaveis, prepara mensagens/campanhas com aprovacao humana e mede retorno, sem envio autonomo nao auditado.

**Acceptance Scenarios**:

1. **Given** um segmento de leads ou alunos com comportamento semelhante, **When** a equipe prepara uma campanha, **Then** o sistema sugere canal, copy, audiencia e objetivo com revisao humana.
2. **Given** um aluno com risco ou baixa aderencia, **When** entra em desafio/comunidade/campanha, **Then** o resultado aparece no contexto do aluno e no BI.

---

### User Story 5 - Abrir experiencias diretas ao aluno e conectividade so depois da base staff-first (Priority: P3)

Como owner do produto, eu quero evoluir para app white label, aulas online, agenda, nutricao, IoT, wearables, pagamentos e multiunidade sem quebrar a confianca operacional do core.

**Why this priority**: Estes modulos do HTML v2 sao estrategicos, mas caros e dependentes de plataforma. Devem vir depois de member intelligence, coach staff-first, compliance, BI e growth estarem maduros.

**Independent Test**: Pode ser validado por slices independentes: agenda, app, nutricional, aulas, IoT, pagamentos, catraca e multiunidade, sempre com degraded/manual states quando a integracao nao existir.

**Acceptance Scenarios**:

1. **Given** uma integracao externa ativa, **When** novos dados chegam ao sistema, **Then** eles alimentam o contexto canonico e ficam visiveis com origem e confianca.
2. **Given** uma academia sem wearable, app ou catraca conectada, **When** a tela correspondente for aberta, **Then** o produto deixa claro que a capacidade esta manual/degradada.

### Edge Cases

- Como manter leads sem consentimento fora de campanhas automaticas?
- Como impedir que app, nutricao por foto, postura por visao computacional ou wearable aparecam como ativos sem integracao real?
- Como preservar a estrategia staff-first quando o HTML pede `coach IA 24/7` para o aluno?
- Como evitar que financeiro, estoque, equipe e agenda criem cadastros paralelos ao member graph?
- Como lidar com academia pequena sem massa suficiente para forecast, cohort, demanda de horarios ou recomendacao nutricional?
- Como separar rede/franquia de multi-tenant atual sem quebrar isolamento por academia?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST criar um `lead-to-member intelligence graph` que combine sinais de captacao, CRM, consentimento, onboarding, check-ins, avaliacoes, bioimpedancia, tarefas, risco, renovacao e upsell.
- **FR-002**: O sistema MUST preservar origem de lead, etapa comercial, consentimentos LGPD e historico de relacionamento apos a conversao para membro.
- **FR-003**: O sistema MUST expandir gestao de alunos com segmentacao comportamental, score de churn/renovacao/upsell, onboarding alem do primeiro mes e roteamento por turno/papel/owner.
- **FR-004**: O sistema MUST introduzir um workspace de coach staff-first antes de qualquer coach conversacional direto para aluno.
- **FR-005**: O sistema MUST suportar progresso, PRs, aderencia ao plano, bioimpedancia, avaliacao fisica e recomendacoes assistidas com override humano.
- **FR-006**: O sistema MUST tratar `Avaliacao Fisica IA` como expansao real de avaliacoes/bioimpedancia, sem inventar postura por visao computacional enquanto nao houver pipeline validado.
- **FR-007**: O sistema MUST introduzir compliance operacional com contrato digital, consentimento de imagem/dados, historico auditavel e alerta de vencimento de termos.
- **FR-008**: O sistema MUST expandir dashboards e reports para cohort, LTV, forecast, receita em risco, inadimplencia, ROI por canal e impacto de follow-ups.
- **FR-009**: O sistema MUST criar foundation de gestao financeira com caixa, contas a pagar/receber, inadimplencia e DRE somente quando houver fonte real de dados.
- **FR-010**: O sistema MUST introduzir gestao de equipe com escala, responsabilidades, performance operacional e NPS por professor sem misturar com RBAC tecnico.
- **FR-011**: O sistema MUST tratar estoque, loja e PDV como modulo posterior, dependente de produto/catalogo/venda real.
- **FR-012**: O sistema MUST expandir captacao e funil pre-lead com landing/captura, tour/aula experimental, chatbot qualificador e score de propensao apenas com consentimento e origem rastreavel.
- **FR-013**: O sistema MUST expandir marketing IA usando CRM, WhatsApp, Kommo, automations, NPS e reports como base canonica, com aprovacao humana e auditoria.
- **FR-014**: O sistema MUST permitir que AI Inbox consuma novos dominios progressivamente: lead, renovacao, upsell, agenda, aderencia, nutricao e comunidade.
- **FR-015**: O sistema MUST introduzir nutricao, agenda, aulas online/hibridas, gamificacao e app white label em releases posteriores, com manual/degraded state quando faltarem dados ou integracoes.
- **FR-016**: O sistema MUST tratar multiunidade/franquia como camada sobre o multi-tenant atual, sem misturar dados entre academias.
- **FR-017**: O sistema MUST tratar wearables, smart equipment, catraca, pagamentos, app mobile e API aberta como workstreams de plataforma conectada, posteriores a fundacao.
- **FR-018**: O sistema MUST manter tenant safety, LGPD, revisao humana, side effects duraveis, observabilidade e degraded states honestos em toda a expansao.

### Key Entities *(include if feature involves data)*

- **Lead-to-Member Intelligence Graph**: contexto canonico que une pre-lead, lead, membro, relacionamento, treino, avaliacao, risco e receita.
- **Consent Record**: aceite de contrato, LGPD, imagem, comunicacao e termos por plano/canal.
- **Acquisition Signal**: origem, campanha, tour, aula experimental, chatbot, score de propensao e comportamento pre-lead.
- **Coach Recommendation**: recomendacao assistida de treino, carga, progressao, avaliacao, aderencia ou recuperacao.
- **Financial Signal**: inadimplencia, receita, plano, margem, fluxo de caixa e receita em risco.
- **Staff Operation Signal**: escala, owner, turno, tarefa, follow-up, performance e NPS associado a professor/equipe.
- **Growth Audience**: segmento acionavel para conversao, renovacao, reativacao, upsell, comunidade ou campanha.
- **Schedule Signal**: aula, agenda, ocupacao, fila, cancelamento, preferencia de horario e comparecimento.
- **Connected Signal**: dado vindo de app, wearable, equipamento, catraca, pagamento ou API externa.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cada milestone deve entregar pelo menos um modulo do HTML v2 em estado operator-ready, manager-ready ou explicitamente manual/degraded.
- **SC-002**: 0 modulos do HTML v2 podem aparecer como ativos sem fonte real de dados, integracao, contrato operacional ou estado manual/degradado.
- **SC-003**: O grafo lead-to-member deve ser consumido por pelo menos quatro superficies: Profile 360, AI Inbox, dashboards/reports e CRM/growth.
- **SC-004**: O primeiro bloco de AI Coach deve gerar valor para professor antes de qualquer experiencia direta para aluno.
- **SC-005**: Captacao, marketing, contratos e comunidade devem respeitar consentimento e trilha auditavel.
- **SC-006**: A expansao completa deve preservar os principios do projeto: verdade operacional, human review, tenant safety, LGPD e side effects observaveis.

## Assumptions

- O HTML `ai_first_os_academia_v2.html` e uma visao de plataforma completa, nao um backlog executavel em uma unica fase.
- O produto atual ja tem base forte em Members, CRM, Assessments, Body Composition, Retention, Tasks, Reports, Dashboards, AI Inbox, WhatsApp, Actuar e parte de Kommo.
- `Captacao de Leads`, `Compliance LGPD`, `Gestao Financeira`, `Gestao de Equipe`, `Estoque & Loja`, `Gamificacao`, `App White Label`, `Multi-unidades`, `Aulas Online`, `IoT` e `Student Companion` exigem novas fases.
- A primeira execucao continua sendo `7.0`, mas agora com escopo explicitamente `lead-to-member`, nao apenas `member`.
- App do aluno, nutricao por foto, visao computacional, voz, wearable e smart equipment entram somente depois da base staff-first e dos contratos de dados estarem maduros.
