# Actuar Bridge local

Ponte local para o AI GYM OS automatizar o Actuar usando a sessao ja aberta do operador.

## Modos

- `dry-run`: prova o fluxo da ponte sem tocar no navegador
- `attached-browser`: conecta em um Chrome/Edge local com remote debugging e tenta usar a aba do Actuar ja aberta

## Pareamento

1. No AI GYM OS, gere um codigo em `Settings > Actuar`
2. Na estacao local, rode:

```bash
python -m actuar_bridge.main pair --api-base-url https://api.exemplo.com --pairing-code ABCD-1234 --device-name "Recepcao 01"
```

## Execucao

```bash
python -m actuar_bridge.main run --api-base-url https://api.exemplo.com --mode dry-run
```

Para usar a aba local do navegador, inicie o Chrome/Edge com remote debugging e rode:

```bash
python -m actuar_bridge.main run --api-base-url https://api.exemplo.com --mode attached-browser --debug-url http://127.0.0.1:9222
```

### Chrome no Windows

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:TEMP\actuar-bridge-profile"
```

### Edge no Windows

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="$env:TEMP\actuar-bridge-profile"
```

Depois:

1. faca login no Actuar nessa janela
2. deixe a aba do Actuar aberta
3. rode o bridge em `attached-browser`

## O que esta comprovado

- pareamento por codigo temporario
- heartbeat da estacao
- claim/completion/failure dos jobs `local_bridge`
- isolamento para o worker nao roubar jobs da ponte local
- executor anexado validado com DOM simulado do Actuar

## O que ainda precisa de validacao ao vivo

- conferir os seletores na aba real do Actuar
- ajustar o mapeamento final dos campos se a tela real divergir do DOM simulado
