# Auditoria Segura do Cordex Gym OS

Harness descartavel para auditar o working tree atual em Docker e observar a borda publicada sem autenticacao.

## Uso

No PowerShell/Prompt de Comando, a partir do repositorio:

```text
audit\audit.cmd all
```

O fluxo `all`:

1. gera projeto Docker, portas e segredos aleatorios em `%TEMP%`, fora do Git;
2. sobe apenas PostgreSQL, Redis, API e frontend em rede interna sem egress;
3. aplica migrations e remove somente o tenant legado vazio criado pela migration;
4. cria Alpha/Beta, cinco papeis por tenant e dados `TESTE_AUDITORIA_`;
5. comprova que worker, scheduler, canais, IA paga, Actuar, Kommo e autoenvio estao desligados;
6. executa API/RBAC/tenant, Playwright seguro, auditoria estatica, borda publica e gates existentes;
7. gera `docs/audits/2026-07-10-cordex-gym-os-safe-audit.md`;
8. remove containers, rede, volume, banco, contas, tokens e segredos temporarios.

Comandos separados para diagnostico controlado:

```text
audit\audit.cmd up
audit\audit.cmd audit
audit\audit.cmd quality
audit\audit.cmd report
audit\audit.cmd status
audit\audit.cmd down
```

`up` deixa o sandbox ativo e, portanto, tambem deixa o arquivo temporario de segredos ativo. Sempre finalize com `down`. O comando `all` usa teardown em `finally` mesmo quando um gate falha.

## Guardrails

- A conta principal e `TESTE_AUDITORIA_GESTOR@teste-auditoria.invalid`, tenant logico `TESTE_AUDITORIA_ALPHA`, slug `teste-auditoria-alpha` e papel `manager`.
- A senha e o token de reset sao gerados em runtime, nunca impressos nem incluidos no relatorio.
- Nenhum `.env` local e lido pelo harness ou enviado ao build Docker.
- Banco e Redis nao publicam portas; frontend e API escutam somente em `127.0.0.1`.
- A rede runtime e `internal: true`; nao existe servico worker.
- O Playwright autenticado desliga trace, HAR, video e screenshot automatico. Screenshots manuais mascarados e ledger de rede sem query/header/body ficam fora do Git.
- A borda publica aceita apenas hosts fixos e usa GET/HEAD/OPTIONS em baixa taxa, sem login ou mutacao.
- Teardown recusa qualquer nome de projeto fora do prefixo `cordex-gym-audit-`.

## Evidencias

Evidencias sanitizadas sao gravadas em `%LOCALAPPDATA%\CordexGymOSAudit\evidence\<run-id>`. O relatorio versionado guarda apenas conclusoes seguras e hashes. Arquivos com nome `trace`, `HAR`, `storage` ou `cookie` sao proibidos pelo teardown.
