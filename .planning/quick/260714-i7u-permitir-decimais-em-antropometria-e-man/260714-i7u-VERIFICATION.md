# Quick Task 260714-i7u - Verification

## Gates locais

Executado em 2026-07-14:

```powershell
npm.cmd test -- --run src/test/MemberBodyCompositionTab.test.tsx src/test/bodyCompositionAnthropometryPreview.test.ts src/test/AuthContext.test.tsx
```

Resultado: `3 passed`, `24 passed`.

```powershell
npm.cmd run build
```

Resultado: build de producao verde (`tsc -b && vite build`).

```powershell
specify check
```

Resultado: `Specify CLI is ready to use!`

```powershell
git diff --check
```

Resultado: sem erros de whitespace; apenas aviso normal de CRLF do Windows.

## Cobertura adicionada

- UI preserva `15.` durante digitacao e aceita `15.1` no campo rapido de dobra subescapular.
- Preview Petroski calcula com dobras decimais.
- AuthProvider atualiza sessao quando o navegador restaura uma pagina aberta.

## Pendente antes de fechar

Nenhum item pendente.

## Publicacao e smoke

```powershell
vercel.cmd deploy --prod --yes
```

Resultado: deployment `dpl_4atPtWqAv9kH4FjSAazZZ9FUGBt1`, `READY`, alias `https://saas-frontend-pearl.vercel.app`.

```powershell
vercel.cmd inspect saas-frontend-alh99au2b-automai.vercel.app
```

Resultado: `status Ready`, target `production`, alias do piloto presente.

```powershell
Invoke-WebRequest -Uri "https://saas-frontend-pearl.vercel.app"
Invoke-WebRequest -Uri "https://saas-frontend-pearl.vercel.app/tasks"
```

Resultado: ambos `200` com `#root` do app carregado.
