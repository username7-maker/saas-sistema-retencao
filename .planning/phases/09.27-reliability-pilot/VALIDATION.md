# Validacao da entrega

## Implementado

- Bioimpedancia e antropometria preservam rascunho, chave de idempotencia,
  contexto de criacao/edicao e isolamento por academia, usuario e aluno.
- Rascunhos legados sao migrados somente apos confirmacao; logout explicito
  remove rascunhos, enquanto expiracao de sessao permite recuperacao posterior.
- A camera inicia com a imagem inteira, mede a resolucao efetivamente entregue,
  prefere camera principal/USB e evita ultra-angular/virtual automaticamente.
- A previa acompanha a proporcao real do stream. Faixas de letterboxing nao sao
  desenhadas no canvas nem enviadas para leitura.
- Captura segmentada permite revisar e refazer topo, centro ou rodape sem perder
  os demais; baixa resolucao aproveitavel gera recomendacao em vez de bloqueio.
- Recorte manual usa quatro cantos e preserva o original em memoria para desfazer.
- Container de teclado, secoes mobile e foco de erro foram reforcados sem alterar
  a expansao permanente do desktop.
- Retencao separa ultima importacao do acesso mais recente e mostra lacunas como
  possivel falta de cobertura, sem recalcular risco automaticamente.
- Publicacao automatica antiga foi desativada. O workflow unico exige SHA completo,
  valida main ou rollback explicito, publica API/worker/frontend e executa smoke
  autenticado somente de leitura antes de registrar o manifesto.

## Verificacoes locais

- Backend: 1.273 testes aprovados; 13 avisos de depreciacao preexistentes.
- Frontend: 226 testes aprovados em 52 arquivos.
- ESLint aprovado.
- TypeScript e build de producao aprovados.
- Bundle: maior chunk 456,06 kB, abaixo do limite de 500 kB.
- `git diff --check` aprovado; workflow YAML validado.

## Validacao que depende do ambiente fisico

- Webcam real e comportamento de foco/exposicao devem ser conferidos no smoke
  do piloto. A selecao automatica principal versus ultra-angular possui teste
  deterministico, mas capacidades reais variam por navegador e dispositivo.
- As flags permanecem administradas pelo ambiente e podem ser desligadas
  isoladamente para rollback.

Nenhum dado de cliente foi alterado por esta implementacao. O arquivo local nao
versionado `saas-backend/6` foi preservado e nao integra a entrega.
