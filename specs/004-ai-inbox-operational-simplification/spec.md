# Feature Specification: AI Inbox Operational Simplification

**Feature Branch**: `004-ai-inbox-operational-simplification`  
**Created**: 2026-04-23  
**Status**: Implemented locally  
**Input**: User description: "Tornar a AI Inbox menos burocratica e mais operacional, sem perder os guardrails auditaveis e a aprovacao humana."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Executar um item normal sem atravessar burocracia (Priority: P1)

Como operador da academia, eu quero abrir um item normal da inbox e preparar a acao em um clique, para conseguir agir rapido sem atravessar telas ou blocos analiticos que nao ajudam a execucao.

**Why this priority**: A inbox ja foi validada como superficie AI-first, mas ainda cria atrito desnecessario para quem so precisa executar a proxima acao.

**Independent Test**: Pode ser testado carregando um item pendente e nao critico, verificando que a UI mostra `Fazer agora` no topo e que um clique prepara a acao com aprovacao implicita registrada.

**Acceptance Scenarios**:

1. **Given** um item pendente e nao critico, **When** o operador abre o item, **Then** a tela mostra um CTA principal unico e uma explicacao curta do que fazer agora.
2. **Given** um item pendente e nao critico, **When** o operador clica no CTA principal, **Then** o sistema aprova implicitamente a recommendation, prepara a acao segura e registra a trilha auditavel correspondente.

---

### User Story 2 - Confirmar itens criticos sem travar a operacao (Priority: P2)

Como operador da academia, eu quero que itens criticos peçam uma confirmacao curta antes da acao, para manter o controle humano sem transformar toda a inbox em uma tela de analise pesada.

**Why this priority**: A fase continua assistiva e supervisionada. Itens criticos ou degradados precisam de aprovacao explicita, mas so eles.

**Independent Test**: Pode ser testado com um item `critical` ou `degraded`, verificando que a acao nao e preparada sem confirmacao explicita e que a confirmacao curta resolve o fluxo.

**Acceptance Scenarios**:

1. **Given** um item critico pendente, **When** o operador tenta preparar a acao, **Then** a UI exige confirmacao explicita antes de chamar a tool layer.
2. **Given** um item critico pendente, **When** o operador confirma a aprovacao, **Then** o sistema registra a aprovacao e prepara a acao segura.

---

### User Story 3 - Separar execucao de analise sem perder observabilidade (Priority: P3)

Como lideranca da academia, eu quero que a tela padrao seja simples para operacao, mas ainda tenha acesso aos detalhes analiticos quando necessario, para nao perder explainability nem metrica.

**Why this priority**: A execucao precisa ser leve para a linha de frente, mas a gestao ainda precisa conseguir abrir detalhes quando houver duvida ou auditoria.

**Independent Test**: Pode ser testado verificando que a lista mostra apenas os campos operacionais e que os detalhes analiticos ficam recolhidos por padrao, sem sumir do produto.

**Acceptance Scenarios**:

1. **Given** a lista principal da inbox, **When** o operador a abre, **Then** ela mostra apenas aluno/lead, severidade, dominio, turno, acao principal e motivo curto.
2. **Given** o inspector de um item, **When** o operador abre os detalhes analiticos, **Then** a tela expande explainability, metadados e observabilidade sem competir com o fluxo principal de execucao.

---

### Edge Cases

- O que acontece quando um item normal ainda esta `pending`, mas a tela precisa aprovar e preparar na mesma acao?
- Como a tela se comporta quando um item esta `critical`, mas a recomendacao e segura e o operador precisa agir rapido?
- Como a inbox trata itens sem `preferred_shift` quando o filtro padrao e `Meu turno`?
- Como a UI mostra itens que ja tiveram acao preparada e agora so precisam de `outcome`?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST apresentar a inbox em modo operador-first por padrao.
- **FR-002**: O sistema MUST mostrar na lista apenas os campos operacionais necessarios para decidir e agir.
- **FR-003**: O sistema MUST expor no payload de lista e detalhe `operator_summary`, `primary_action_type`, `primary_action_label`, `requires_explicit_approval` e `show_outcome_step`.
- **FR-004**: O sistema MUST permitir aprovacao implicita para itens pendentes nao criticos quando o CTA principal for usado.
- **FR-005**: O sistema MUST exigir confirmacao explicita para itens `critical` ou `degraded` antes da preparacao da acao.
- **FR-006**: O sistema MUST manter a tool layer segura ja validada na `4.43`, sem abrir automacao autonoma nova.
- **FR-007**: O sistema MUST manter o filtro `Meu turno / Todos os turnos` como comportamento padrao da inbox.
- **FR-008**: O sistema MUST destacar `Fazer agora`, `Mensagem pronta` ou `Resumo da acao`, `CTA principal` e `Registrar resultado` antes dos detalhes analiticos.
- **FR-009**: O sistema MUST continuar expondo metricas e explainability, mas atras de superficies recolhidas por padrao.
- **FR-010**: O sistema MUST manter a trilha auditavel de aprovacao, preparacao e outcome sem regressao.

### Key Entities *(include if feature involves data)*

- **Operator-first AI Triage Item**: recommendation servida para execucao rapida, com foco na acao principal e motivo curto.
- **Primary Action**: acao operacional principal exibida como CTA unico do item.
- **Explicit Approval Gate**: confirmacao curta exigida somente para itens criticos ou degradados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos itens nao criticos pendentes podem ser preparados com um unico CTA principal.
- **SC-002**: 100% dos itens criticos ou degradados exigem confirmacao explicita antes da preparacao da acao.
- **SC-003**: A lista principal deixa de exibir por padrao estado de aprovacao, estado de execucao, owner, canal e explainability longa.
- **SC-004**: 100% das acoes preparadas continuam deixando trilha auditavel de aprovacao implicita ou explicita, preparacao e outcome.

## Assumptions

- Esta fatia continua reutilizando a arquitetura da `4.43`, sem criar uma segunda inbox.
- A aprovacao humana continua obrigatoria no produto, mas itens normais podem embutir essa aprovacao no CTA principal.
- Turno do login ja foi implantado e deve continuar sendo o comportamento padrao.
- Explainability rica continua existindo, mas deixa de ser a visao primaria da linha de frente.
