# UI Spec - Automation Journeys OS

## Tela

Rota existente: `/automations`.

## Estrutura

- Aba principal: `Jornadas prontas`.
- Aba secundaria: `Regras avancadas`.

## Jornadas prontas

Cada card deve mostrar:

- nome da jornada
- dominio
- status
- inscritos
- proximas acoes
- tasks criadas
- taxa de execucao, quando houver dados
- CTA de preview/ativacao

## Wizard V1

Fluxo curto:

1. escolher template
2. revisar objetivo e etapas
3. gerar preview de elegiveis
4. ativar jornada

## Execucao

Toda acao real aparece em `/tasks` / Work Queue. A tela de automacoes e configuracao e gestao, nao fila de execucao.

## Estados

- ativa
- pausada
- manual/degradada
- erro

## Nao fazer na V1

- canvas visual
- editor livre de workflow complexo
- envio autonomo
- KPIs pesados na tela de recepcao/professor

