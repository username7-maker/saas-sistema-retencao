# Spec 055 - Work Queue Concurrency and Safe External Effects

## User Story

Como operador do Cordex Gym OS, quero que assumir, concluir ou disparar um efeito da fila tenha um unico vencedor observavel, para que outro operador ou retry nao sobrescreva o trabalho nem chame o provider novamente sem consentimento aplicavel.

## Requirements

- Coordenacao persistente tenant-scoped deve cobrir todos os source types da Work Queue sem transformar o sidecar em novo ledger de trabalho.
- Execute/outcome deve usar versao esperada e compare-and-swap na mesma transacao da mutacao e auditoria.
- Conflito deve retornar 409 tipado com claimant/versao atual e caminho recuperavel.
- Unicidade de task operacional ativa deve possuir chave canonica persistente e constraint, com tratamento de `IntegrityError` como reuso da vencedora.
- Consentimento deve depender de canal, efeito e finalidade, nunca apenas de `require_auto_send`.
- `AutopilotAction` deve persistir intent, fingerprint, consent snapshot e chave tenant-scoped unica antes do provider.
- Repeticao da mesma chave/hash reapresenta o intent existente; hash diferente retorna conflito.
- Estado incerto depois de chamar provider nao pode gerar retry automatico.
- Nao ha envio autonomo nem ampliacao de RBAC.

## Acceptance Criteria

- Duas sessions PostgreSQL disputando claim/outcome produzem um vencedor, um 409 e um unico evento.
- Duas criacoes concorrentes com a mesma chave canonica resultam em uma task ativa.
- Consentimento ausente, revogado, expirado ou cross-tenant produz zero chamadas ao provider.
- Mesma effect key concorrente cria uma intent e chama provider no maximo uma vez localmente.
- Falha/estado incerto permanece duravel e replay nao dispara automaticamente.
- Testes usam PostgreSQL real, sessions independentes e provider sintetico.

## Non-Goals

- Garantia de entrega exatamente uma vez quando o provider nao oferece idempotencia nativa.
- Lease/override gerencial completo.
- Ledger de consentimento novo para lead.
- Materializacao de `assessment_queue` como Task.
