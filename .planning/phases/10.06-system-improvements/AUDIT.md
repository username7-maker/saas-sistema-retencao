# Varredura do Gym OS — 06/10/2026

## Escopo e método

Revisão transversal de páginas, serviços e contratos de tarefas, retenção, avaliações com e sem bioimpedância, importações, exportações, financeiro, usuários e integrações. Inventário adicional de rotas de autenticação, CRM, notificações, relatórios e automações. Consultas agregadas e somente leitura na academia piloto; nenhuma alteração de cadastro, avaliação, tarefa, permissão ou integração. Nenhuma publicação nesta rodada.

Esta é uma varredura ampla de código, testes e indicadores, não uma certificação de cada interação em todos os aparelhos. Não foram executados envios reais para Actuar/WhatsApp, testes físicos de webcam ou uma nova extração paga por IA. O código local contém alterações anteriores; a suíte valida esse checkout, e não garante equivalência byte a byte com todos os serviços publicados.

## Correções prioritárias

### 1. Horário do dia operacional — defeito reproduzido

`saas-backend/app/services/finance_service.py:133` usa a data UTC para caixa diário; a linha 271 usa UTC para considerar uma conta vencida. Simulação local com o próprio `_normalize_entry_status`, sem persistência: às **22:30 de 06/10 em São Paulo**, uma conta aberta com vencimento **06/10** tornou-se `overdue`, porque em UTC já era 07/10. O esperado para a academia é permanecer aberta até o fim do dia local.

`task_service.py:263` e `:314` também usam meia-noite UTC para filtros “hoje”, “atrasadas” e métricas diárias. `export_service.py:70` aplica dias UTC e imprime `data_checkin`/`hora` sem conversão para o horário operacional. Um check-in às 22h locais equivale a 01h UTC no dia seguinte; a seleção por data e a coluna humana precisam seguir uma mesma convenção explícita.

**Proposta:** centralizar limites do dia em America/Sao_Paulo, mantendo os timestamps persistidos em UTC. Regressões obrigatórias às 20:59, 21h, 23:59 e 00h locais, caixa, vencimento, tarefas e exportação. Conferir compatibilidade dos importadores antes de mudar os aliases da planilha; não reescrever o histórico automaticamente.

### 2. Permissões inconsistentes na tela de tarefas — confirmado no contrato

`saas-frontend/src/pages/tasks/TasksPage.tsx:135` oferece “Nova Tarefa” sem condicionar o papel. `saas-backend/app/routers/tasks.py:43` permite criar somente a owner, manager, receptionist e salesperson. O professor vê uma ação que a API rejeita. Na mesma página, `usersQuery` solicita `/users` sem `enabled`; `routers/users.py:179` restringe a listagem a owner/manager. Isso também causa requisições não autorizadas para outros perfis.

**Proposta:** alinhar visibilidade e carregamento com as permissões já definidas, sem ampliar acesso por conveniência. Testar os cinco perfis e o fluxo do professor.

### 3. Atualização incompleta após mudanças de tarefas — lacuna confirmada no código

`TasksPage.tsx:73,83,92` invalida somente `tasks` após criar, editar ou excluir. `WorkExecutionView.tsx:360,367,374` mantém `work-queue` fresca por 60 segundos. As próprias mutações da execução invalidam ambos os grupos. A lista e o modo execução podem, portanto, mostrar estados diferentes até uma nova consulta; falta invalidar também os painéis relacionados. A reprodução visual em navegador autenticado ainda é pendente.

**Proposta:** um contrato compartilhado de atualização de tarefas/fila/painéis. Teste de alternar abas imediatamente após concluir, reagendar ou excluir, sem depender de recarregar a página.

## Melhorias operacionais e desempenho

### 4. Carregamento integral de tarefas

`TasksPage.tsx:40` carrega tarefas e índices de alunos/usuários logo na abertura. `taskService.ts:77` percorre todas as páginas sequencialmente em `listAllTasks`, mesmo antes de o usuário precisar da lista completa.

A consulta agregada encontrou **8.831 tarefas abertas não arquivadas**, das quais **6.550 vencidas** e **6.216 sem responsável**, excluindo registros deletados. Os subconjuntos se sobrepõem. Esse total inclui fontes que a lista padrão pode filtrar; não representa o número exato carregado por cada perfil nem comprova latência medida.

**Proposta:** paginação no servidor, busca/filtros no servidor e carregamento por aba. Triar o estoque por origem e idade com a limpeza operacional existente, sempre com prévia e preservação do histórico; não concluir em massa só para melhorar indicadores.

### 5. Actuar: bloqueios precisam de tratamento orientado

Aplicando a mesma escolha da avaliação mais recente por aluno usada em `body_composition_actuar_sync_service.py:456`, foram encontrados **43** registros `member_not_linked`, **20** `member_match_ambiguous`, **14** `critical_fields_missing` e **1** `csv_export_ready` em `manual_sync_required`.

São bloqueios registrados, não prova de queda atual do serviço. A seleção considera a avaliação mais recente, sem um filtro adicional de aluno deletado, tal como o serviço atual. No histórico completo, os 5 casos `actuar_form_changed` são de abril; não devem ser apresentados como erro recente.

**Proposta:** mostrar motivo e ação específica por item: vincular por identificador confirmado, revisar duplicidade, completar campos do exame ou baixar arquivo. Separar “salvo localmente”, “aguarda revisão” e “enviado”. Nunca escolher automaticamente uma pessoa em resultado ambíguo.

### 6. Importação: comunicar sucesso parcial

`ImportsPage.tsx:637` mostra “Importação de alunos concluída” independentemente do número de linhas com pendência; o resumo detalhado existe, mas a mensagem principal não diferencia resultado parcial. Para check-ins já há uma mensagem com quantidade importada e pendente.

**Proposta:** padronizar contagens criadas/atualizadas/ignoradas/pendentes, com acesso direto ao CSV de pendências. Isso reduz a impressão de que um cadastro desapareceu quando foi bloqueado por identidade insuficiente.

### 7. Avaliações: validação visível antes de calcular

As regras de unidades e as mensagens específicas corrigidas anteriormente estão cobertas pelos testes. Ainda há oportunidade de destacar o campo inválido na própria tela, além do aviso temporário, e deixar `(mm)` explícito nas dobras, preservando `(cm)` em todas as medidas de fita. Não converter um valor automaticamente de uma unidade para outra.

**Proposta:** validação contextual por protocolo, resumo persistente de pendências e foco no primeiro campo inválido. Manter a distinção entre medidas observadas, calculadas e ausência de evidência OCR. Validar captura/rotação/recorte/zoom em uma webcam real da academia antes de declarar qualidade física comprovada.

### 8. Rastreabilidade e cobertura

`.planning/STATE.md` está desatualizado em relação aos registros recentes de entrega. O checkout contém alterações pendentes prévias. Publicações por CLI precisam de um manifesto com hash dos arquivos, versões, testes e IDs de implantação, sem exigir envio ao GitHub.

**Proposta:** registrar versão reproduzível e rollback, testes de permissões entre UI/API e testes de virada do dia. Os testes atuais passam, mas não cobrem adequadamente os defeitos acima. Atualizar dependências depreciadas de teste e a base Browserslist em manutenção separada, não misturada com correções de negócio.

## Verificação realizada nesta rodada

- Backend: **1.426 testes aprovados, 3 ignorados**, 23 avisos de depreciação.
- Frontend: **351 testes aprovados em 59 arquivos**. Logs de erro provocados pelos testes de falha não representam teste reprovado.
- ESLint e TypeScript: saída 0.
- Build Vite de produção e verificação de orçamento dos bundles: aprovados.
- API piloto `/health/ready`: HTTP 200 durante a verificação.
- Logs recentes da implantação: não foi identificado incidente novo nesse recorte. O histórico disponível após deploy não permite concluir ausência de incidentes nas últimas semanas.
- Consultas de banco somente leitura e agregadas, sem reprodução de dados pessoais no relatório.

## Ordem recomendada

1. Corrigir calendário operacional e permissões de tarefas, com testes dos casos ausentes.
2. Unificar atualização da fila/painéis e comunicar importações parciais.
3. Paginar tarefas e organizar pendências da Actuar, com revisão de identidade.
4. Melhorar feedback da avaliação e concluir validação física do scanner.
5. Atualizar documentação de implantação e manter monitoramento com identificadores de erro.

Nenhum dado real foi alterado para produzir este relatório.
