# saas-frontend

Frontend React 18 + TypeScript do AI GYM OS.

## Rodar local

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

## Variaveis

- `VITE_API_BASE_URL=http://127.0.0.1:8000`
- `VITE_WS_BASE_URL=ws://127.0.0.1:8000` (opcional)

## Rotas principais

- `/dashboard/executive`
- `/dashboard/operational`
- `/dashboard/commercial`
- `/dashboard/financial`
- `/dashboard/retention`
- `/crm`
- `/tasks`
- `/goals`
- `/notifications`

## Login multi-tenant

Use os campos:

- `Academia (slug)`
- `E-mail`
- `Senha`

## E2E

```bash
npm run test:e2e
```
