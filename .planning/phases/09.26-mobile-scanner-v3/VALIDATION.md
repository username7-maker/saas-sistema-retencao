# Validacao - Phase 09.26

## Local

- Backend completo: `1268 passed`.
- Frontend completo: `219 passed` em 51 arquivos.
- Frontend lint: aprovado.
- Build TypeScript/Vite: aprovado.
- Bundle: maior chunk 455,71 kB; limite de 500 kB aprovado.
- Dependencias de producao: `npm audit --omit=dev` sem vulnerabilidades.
- Alembic: `20260908_0062` e o unico head.
- Testes focados novos: idempotencia com repeticao e conflito; aceite e limite
  de imagens segmentadas; contratos antigos de imagem preservados.

## Imagem de referencia

- A imagem fornecida foi lida apenas em memoria.
- Entrada: 899 x 1599; saida: 1000 x 2874.
- Metodo: `receipt_perspective+background_normalization+clahe`.
- Confianca do contorno: 0,82.
- Papel detectado em aproximadamente 61,81% do quadro.
- Largura curta util antes da ampliacao: 556 px.
- Nenhum codigo de baixa qualidade foi gerado.
- Nenhuma copia processada foi salva.

## Antes da producao

- Backup logico atual gerado em 09/09/2026 no volume seguro destacado:
  `cordex-supabase-20260909.dump`, 40.768.685 bytes, SHA-256
  `4f2e8a26638ff0336b356c9bf26ce75828fade9516db3318daa813b5ea8bc292`.
- O dump passou por `pg_restore --list` antes de receber o marcador `.ready`.
- O job temporario foi removido e o volume permaneceu destacado da aplicacao.
- Confirmar saude/cota do Supabase.
- Aplicar `20260908_0062` antes da API nova.
- Confirmar variaveis e flags da academia piloto.
- Executar smoke publico e autenticado sem destinatario real.
- Validar webcam USB fisica; essa verificacao nao pode ser simulada pela suite.

## Producao

Pendente. Nenhum deploy ou alteracao de dados de cliente foi executado durante
esta validacao local.
