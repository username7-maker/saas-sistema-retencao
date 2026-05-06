# Context - 04.43.10 Regua Tecnica Pos-Avaliacao

## Problema

Cada avaliacao salva precisa gerar compromisso tecnico para o professor, nao apenas registro historico. O piloto ja tinha follow-up D+14, mas faltavam duas garantias operacionais: conferir se o treino foi entregue apos a avaliacao e lembrar a reavaliacao no prazo correto.

## Decisao

A regua sera regra de dominio em `assessment_service`, nao automacao generica. Ao salvar avaliacao, o backend cria tasks tecnicas idempotentes para D+8, D+14 e reavaliacao. A Work Queue mostra essas tasks somente quando a janela operacional chegar.

## Escopo V1

- Criar tasks tecnicas em toda nova avaliacao.
- Atribuir professor pelo turno preferido do aluno quando possivel.
- Preservar historico e cancelar apenas tasks futuras abertas da regua anterior.
- Expor etapa tecnica e CTA na Fila do Professor.
- Adicionar outcomes tecnicos rapidos.

## Fora de escopo

- Envio automatico de WhatsApp.
- Editor de automacoes.
- Mudanca de contrato publico de criacao de avaliacao.
- Nova tabela para a regua tecnica.
