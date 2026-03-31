# Actuar Bridge extension

Extensao Chrome/Edge para simplificar a ponte local do Actuar.

## Objetivo

- anexar explicitamente a aba real do Actuar
- evitar que a operacao precise abrir o navegador com flags de debugging como passo principal
- receber jobs do relay local em `127.0.0.1:44777`

## Como carregar no Chrome/Edge

1. abra `chrome://extensions` ou `edge://extensions`
2. ative `Modo do desenvolvedor`
3. clique em `Carregar sem compactacao`
4. selecione esta pasta `actuar_bridge_extension`

## Como usar

1. rode o app local do bridge em modo `extension-relay`
2. abra e faça login no Actuar
3. na aba do Actuar, abra o popup da extensao
4. clique em `Anexar aba atual`
5. deixe o popup fechado; a extensao continua trabalhando em background

## Limites honestos

- a extensao depende da estrutura DOM real do Actuar
- se a tela real divergir, os seletores do `content.js` precisam de ajuste
- o relay local precisa estar online em `127.0.0.1:44777`
