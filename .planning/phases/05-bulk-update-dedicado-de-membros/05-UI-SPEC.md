---
phase: 05
slug: bulk-update-dedicado-de-membros
status: approved
shadcn_initialized: false
preset: not applicable
created: 2026-03-24
---

# Phase 05 - UI Design Contract

> Visual and interaction contract for the dedicated bulk update flow under the members module.

## Layout Contract

- A experiencia vive como sub-rota do modulo de membros, com um CTA claro saindo de `MembersPage`.
- Estrutura recomendada da tela:
  - header com objetivo e aviso de seguranca
  - card de upload + regras de match
  - bloco de preview com resumo agregado
  - diff principal por linhas/campos
  - barra de confirmacao final
- Nao criar wizard com multiplas paginas. O fluxo deve continuar legivel em uma unica superficie operacional.

## Interaction Contract

- Sequencia fixa:
  - selecionar arquivo
  - validar preview
  - revisar linhas/campos alterados
  - confirmar atualizacao em massa
- O botao final permanece desabilitado enquanto houver linhas invalidas, ambiguidade de match ou preview desatualizado.
- O preview deve permitir exportar pendencias/erros para correcoes externas se isso surgir naturalmente do backend.
- A tela precisa evidenciar que este fluxo atualiza somente membros ja existentes.

## Copy Contract

- Titulo: `Atualizacao em massa de membros`
- Helper: `Envie um arquivo corretivo para atualizar membros existentes com preview antes do commit.`
- Regras de match: `Use member_id, matricula ou email para identificar cada membro.`
- CTA primaria: `Validar atualizacao`
- CTA final: `Confirmar atualizacao em massa`
- Estado bloqueado: `Corrija as linhas pendentes antes de confirmar.`

## Diff Contract

- Cada linha relevante precisa mostrar:
  - identificador usado no match
  - membro encontrado
  - campos alterados com `valor atual -> novo valor`
  - status da linha
- Status minimos:
  - `Pronta`
  - `Nao encontrada`
  - `Ambigua`
  - `Invalida`

## Safety Contract

- Nao usar vermelho para tudo; diferenciar erro bloqueante de aviso.
- Nao esconder linhas ignoradas ou invalidas; elas precisam aparecer para auditoria do operador.
- A superficie deve deixar claro que nao ha criacao de membros neste fluxo.

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS
