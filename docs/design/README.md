# Design — onde colocar referências visuais (OpenDesign)

O Cordex Gym OS **já tem UI construída** (`saas-frontend/`). Esta pasta serve para
**evoluções visuais**: redesign de telas, telas novas, ou um design system oficial.

## O que fazer (você, fundador)

1. Exporte do **OpenDesign** (ou de onde estiver o design): HTML/CSS, PDF, PNGs por tela
   ou tokens JSON de cores/tipografia.
2. Coloque tudo dentro de `raw/` (nomeie por tela: `painel.png`, `crm.png`...).
3. Rode **`/a360-vamos`** no Claude Code — o time lê, mostra o que entendeu e planeja a
   aplicação do design nas telas existentes.

Se não houver export, o time evolui a UI seguindo o padrão visual já presente no
`saas-frontend/` (Tailwind + componentes existentes).

## Estrutura

```
docs/design/
├── README.md            # este arquivo
├── raw/                 # <- export do OpenDesign entra aqui
└── DESIGN-OVERVIEW.md   # (gerado pelo time ao ler o raw/) mapa de telas + tokens
```
