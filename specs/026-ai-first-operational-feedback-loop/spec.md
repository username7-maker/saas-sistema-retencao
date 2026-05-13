# Spec 026 - AI First Operational Feedback Loop

## User Story

Como gestor ou operador, quero revisar rascunhos de IA marcando se aproveitei, editei, rejeitei ou escalei, para que o AI Gym OS aprenda operacionalmente quais assistencias sao uteis antes de aumentar automacao.

## Functional Requirements

- A Central de Revisao IA deve aceitar feedback humano para cada item.
- Decisoes aceitas: `approved`, `edited`, `rejected`, `escalated`.
- `edited` deve persistir o texto editado como rascunho atual.
- `rejected` deve manter o comportamento de rejeicao existente.
- Toda decisao deve registrar evento auditavel em `AutopilotEvent`.
- Metricas devem expor total revisado, aprovados, editados, rejeitados, escalados e taxa de aproveitamento.
- Preparar na Kommo deve ser tratado como aprovacao implicita quando ainda nao houver feedback registrado.

## Non-Functional Requirements

- Sem autoenvio.
- Sem nova tabela na V1.
- Tenant safety obrigatoria.
- Role access igual a Central de Revisao IA existente.
- Estados bloqueados/sensiveis nao podem ser tratados como sucesso simples.

