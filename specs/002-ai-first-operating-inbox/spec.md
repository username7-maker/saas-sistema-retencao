# Feature Specification: AI-First Operating Inbox

**Feature Branch**: `002-ai-first-operating-inbox`  
**Created**: 2026-04-16  
**Status**: Ready  
**Input**: User description: "Transformar os HTMLs `ai_first_os_academia.html` e `diagnostico_ai_gym_os.html` em um recorte executavel do AI GYM OS, comecando pela primeira superficie AI-first real e respeitando o roadmap atual."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Priorizar quem atacar hoje em uma unica inbox (Priority: P1)

Como owner ou manager da academia, eu quero abrir o sistema e receber uma inbox unica de prioridades diarias para retencao e onboarding, para decidir rapidamente quem precisa de acao hoje sem depender de varias telas para montar essa ordem manualmente.

**Why this priority**: Este e o primeiro corte realmente AI-first do produto. Sem essa mudanca, a IA continua acessoria e a decisao principal permanece fragmentada.

**Independent Test**: Pode ser testado de forma independente validando que a inbox mostra itens de retencao e onboarding no mesmo fluxo, com explicacao clara do motivo da prioridade e sem exigir que o usuario comece por dashboards, tasks ou abas separadas.

**Acceptance Scenarios**:

1. **Given** um owner com alunos e leads em risco ou onboarding ativo, **When** ele abre a inbox AI-first, **Then** o sistema mostra uma fila unificada com prioridade diaria e explicacao objetiva de "por que agora".
2. **Given** um item priorizado da inbox, **When** o usuario o abre, **Then** o sistema mostra a proxima melhor acao, o canal recomendado, o owner recomendado e o impacto esperado.

---

### User Story 2 - Aprovar acao item por item com seguranca (Priority: P2)

Como operador da academia, eu quero aprovar ou rejeitar cada recomendacao individualmente, para aproveitar a velocidade da IA sem perder controle sobre mensagens, tarefas e follow-ups.

**Why this priority**: O valor operacional da inbox depende de transformar recomendacao em acao, mas a fase continua sujeita a aprovacao humana obrigatoria e a canais auditaveis.

**Independent Test**: Pode ser testado de forma independente aprovando e rejeitando itens da inbox e verificando que o sistema so prepara acoes permitidas pelo contrato desta fase, sempre com trilha de decisao.

**Acceptance Scenarios**:

1. **Given** uma recomendacao pronta para acao, **When** o operador aprova o item, **Then** o sistema prepara a acao suportada e registra quem aprovou, o que foi aprovado e o estado posterior.
2. **Given** uma recomendacao pronta para acao, **When** o operador rejeita o item, **Then** o sistema registra a rejeicao sem executar nenhum side effect.

---

### User Story 3 - Medir se a inbox melhora a operacao (Priority: P3)

Como lideranca do produto ou da operacao, eu quero medir aceitacao e resultado das recomendacoes da inbox, para saber se a primeira superficie AI-first realmente melhora triagem e execucao, em vez de parecer sofisticada sem gerar impacto.

**Why this priority**: Sem medicao de aceitacao e resultado, a fase corre o risco de virar apenas uma nova interface, e nao uma mudanca de loop operacional.

**Independent Test**: Pode ser testado de forma independente verificando que cada recomendacao aprovada ou rejeitada deixa trilha suficiente para comparar a operacao com o baseline manual ja definido para a `4.43`.

**Acceptance Scenarios**:

1. **Given** uma recomendacao aprovada, **When** a acao decorrente acontece, **Then** o sistema registra o encadeamento entre sugestao, aprovacao, execucao e resultado observado.
2. **Given** o uso continuo da inbox no piloto, **When** a lideranca revisa a superficie, **Then** existem indicadores suficientes para comparar tempo de triagem, aceitacao da recomendacao e volume de acoes executadas contra o baseline manual.

---

### Edge Cases

- Como a inbox deve se comportar quando um item tem contexto insuficiente para recomendar canal, owner ou mensagem com confianca?
- O que acontece quando o estado do membro ou lead muda entre a recomendacao e a aprovacao humana?
- Como a superficie trata canais ou integracoes temporariamente degradados sem esconder que a acao precisara de fallback manual?
- Como a fila deve responder quando nao houver itens relevantes para retencao ou onboarding no dia?
- Como o sistema evita apresentar como "pronto" modulos futuros do conceito amplo, como coach pessoal, nutricao ou wearables, se eles ainda nao existem no produto?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST fornecer uma inbox AI-first unificada para retencao e onboarding como primeira superficie operacional desta fase.
- **FR-002**: O sistema MUST exibir para cada item da inbox uma explicacao clara do motivo da prioridade atual.
- **FR-003**: O sistema MUST exibir para cada item a proxima melhor acao, o canal recomendado, o owner recomendado e o impacto esperado.
- **FR-004**: O sistema MUST permitir aprovacao ou rejeicao item por item antes de qualquer execucao ligada a recomendacoes da inbox.
- **FR-005**: O sistema MUST limitar as acoes preparadas nesta fase a tarefas, follow-ups, mensagens preparadas e jobs aprovados que respeitem o contrato seguro ja definido para `4.43`.
- **FR-006**: O sistema MUST registrar para cada recomendacao o estado de sugestao, aprovacao ou rejeicao, execucao e resultado observado.
- **FR-007**: O sistema MUST expor de forma honesta estados degradados, manuais ou de fallback quando canal, dado ou integracao nao permitirem automacao segura.
- **FR-008**: O sistema MUST permitir que o usuario continue do item da inbox para o contexto detalhado do membro ou lead sem perder o raciocinio da recomendacao.
- **FR-009**: O sistema MUST respeitar os mesmos guardrails de tenant, auditoria e aprovacao humana ja definidos para o produto atual.
- **FR-010**: O sistema MUST funcionar usando os dados operacionais ja existentes do AI GYM OS, sem depender de app do aluno, wearable ou nutricao para entregar valor nesta fase.
- **FR-011**: O sistema MUST manter explicitamente fora do escopo desta feature os modulos de coach pessoal do aluno, geracao automatica de treino, nutricao, wearables, agendamento por previsao de demanda e suite ampla de marketing IA.
- **FR-012**: O sistema MUST produzir evidencia suficiente para comparar a operacao via inbox com o baseline manual definido para a `4.43`.

### Key Entities *(include if feature involves data)*

- **AI Triage Item**: Unidade priorizada de trabalho diario que representa um membro ou lead com contexto suficiente para recomendacao operacional.
- **Recommended Action**: Acao sugerida pela IA com canal, owner, mensagem opcional e impacto esperado.
- **Approval Decision**: Registro da aprovacao ou rejeicao humana associada a uma recomendacao especifica.
- **Outcome Observation**: Resultado operacional posterior usado para medir se a recomendacao gerou execucao util.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos itens exibidos na inbox mostram motivo da prioridade, acao recomendada, canal recomendado e owner recomendado.
- **SC-002**: 100% das acoes executadas a partir da inbox possuem registro anterior de aprovacao ou rejeicao humana.
- **SC-003**: A operacao do piloto consegue iniciar a triagem diaria por uma unica superficie que combina retencao e onboarding, sem depender de duas filas iniciais separadas.
- **SC-004**: 100% das recomendacoes aprovadas no escopo da fase deixam trilha auditavel de sugestao, aprovacao, execucao e resultado observado.
- **SC-005**: 0 modulos ainda inexistentes no produto aparecem para o usuario como capacidades ativas desta feature.

## Assumptions

- Esta spec traduz o conceito amplo dos HTMLs para um primeiro recorte executavel, e nao tenta implementar o "AI-first OS" completo em uma unica fase.
- A primeira superficie AI-first do produto continua sendo a `AI Triage Inbox` ja definida na `4.43`.
- O produto permanece em freeze lateral ate os gates de hardening e piloto serem fechados.
- A feature deve reaproveitar os dados e superficies ja existentes de retencao, onboarding, tasks, CRM e contexto do membro.
- Coach pessoal do aluno, treino IA, nutricao, IoT/wearables e marketing IA amplo permanecem como visao futura, fora desta entrega.
