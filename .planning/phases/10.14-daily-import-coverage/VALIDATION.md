# Validação — 14/10/2026

## Entrega local

- Preview de check-ins inclui dias observados e dias pendentes. Mantém âncora histórica na auditoria da academia; o último acesso legado é a referência inicial quando não existe cobertura registrada. Não afirma reconstruir todos os arquivos anteriores à implantação.
- Aviso antes da importação com as datas e confirmação explícita. Backend revalida a lista: sem ciência da lista atual, HTTP 409 antes de qualquer gravação.
- A importação e sua cobertura ficam na mesma transação/audit log existente. Arquivos com linhas rejeitadas não marcam seus dias como completos; arquivos só com duplicatas e sem erros podem completar a cobertura.
- Dias sem movimento não são distinguidos automaticamente de academia fechada ou exportação incompleta. Aviso informa essa limitação e permite continuar conscientemente, sem esconder a lacuna no histórico.
- Não altera timestamps históricos, regras de risco, identificação de alunos, rate limits ou isolamento por academia. Não repete POST automaticamente.

## Demora e tentativas repetidas

- Confirmado no código anterior: as oito rotas async de importação/preview faziam parsing, SQL síncrono e recálculo no event loop. Convertidas para rotas síncronas, executadas no worker pool padrão do FastAPI, incluindo leitura limitada do UploadFile. Teste HTTP verifica execução em worker e confirma o contrato transacional.
- Acrescentados logs agregados de duração/quantidade para preview e importação de check-ins, sem nomes ou conteúdo de linhas. Permitem distinguir demora de validação e aplicação nos próximos incidentes.
- Mensagens específicas para 429 e timeout. Em timeout, o cliente orienta revalidar para saber o que foi persistido; não promete rollback nem repete automaticamente uma mutação.
- Não foi reproduzida nesta rodada uma falha real da academia. A consulta aos logs recentes não forneceu evidência suficiente para atribuir todas as tentativas repetidas a uma causa única. Não se afirma ganho medido de latência em produção.

## Testes

- Backend completo: **1.431 passed, 3 skipped**, 23 warnings de depreciação.
- Frontend completo: **352 passed / 59 arquivos**; depois foi acrescentado e executado o teste de FormData com a lista exata de confirmação. Testes direcionados finais: **8 passed** (5 da página e 3 de download/importação). Total de casos exercitados nesta rodada: 353.
- ESLint completo e novamente nos arquivos finais: exit 0.
- TypeScript final: exit 0.
- Build Vite final e orçamento de bundles: exit 0.
- Regressões: dia 11→13, lacuna persistente em dia 14, recuperação de 12, sobreposição, arquivo inicial e histórico anterior, lacuna interna, parcial, seleção por academia, confirmação ausente/obsoleta, cancelamento no navegador, confirmação positiva, processamento em worker, rollback de auditoria existente e duplicatas existentes.

## Publicação

Não publicado, sem push para GitHub e sem alterações de dados de produção. Implantar API e frontend em sequência curta: a API nova exige confirmação das lacunas e o frontend antigo não conhece essa confirmação. Nenhuma migração necessária. Validar com uma planilha real autorizada após a publicação, monitorando os novos eventos `checkin_preview_timing` e `checkin_import_timing`.
