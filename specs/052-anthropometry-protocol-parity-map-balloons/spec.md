# Spec 052 - Anthropometry Protocol Parity + Measurement Balloons

## Summary
Expandir a Bioimpedancia v2 para calcular automaticamente os protocolos antropometricos restantes que possuem formula publica e campos ja capturados pelo Cordex, mantendo como manual review os metodos que dependem de variaveis ausentes. Reorganizar o mapa corporal do relatorio para mostrar um boneco grande, sem foto do aluno, com baloes de medidas ao redor do corpo.

## Goals
- Implementar calculo automatico para protocolos publicos suportaveis alem de Petroski masculino.
- Manter paridade operacional com o Actuar apenas onde a formula e os campos obrigatorios sao conhecidos e reproduziveis.
- Bloquear calculo automatico para protocolos que exigem raca, maturacao, circunferencia iliaca ou outros campos ainda nao capturados.
- Exibir no relatorio um mapa corporal grande com figura unica e baloes de perimetria, em vez de uma imagem pequena de folha completa.
- Preservar `body_fat_used_percent` como unico percentual oficial para relatorio, IA, cards, WhatsApp e Kommo.

## Non-goals
- Nao copiar layout, codigo, marca, assets proprietarios ou logica proprietaria do Actuar.
- Nao criar modulo paralelo de avaliacao fisica.
- Nao alterar schema, rotas, OCR, sync Actuar, WhatsApp ou Kommo nesta rodada.
- Nao inventar formulas para protocolos sem fonte publica ou sem campos capturados.
- Nao usar foto de aluno.
- Nao substituir massa muscular da bioimpedancia por estimativa antropometrica.
- Nao apresentar percentual de gordura como diagnostico clinico.

## Protocol Policy
- Protocolos com formula publica e campos existentes no Cordex podem preencher `body_fat_anthropometric_percent` e, quando selecionados, `body_fat_used_percent`.
- Protocolos que exigem campos ausentes ficam selecionaveis para registro, mas retornam `anthropometry_protocol_manual_only`.
- O sistema deve validar idade, sexo e medidas antes de calcular.
- O relatorio deve rotular qualquer resultado como estimativa operacional.

## Acceptance Criteria
- Backend e frontend calculam os mesmos resultados para Macardle/YMCA adulto, Guedes adulto, Petroski feminino, Weltman feminino, Slaughter simples e Faulkner quando campos suficientes existem.
- Protocolos com raca/maturacao/circunferencia iliaca ausentes permanecem manual-only e nao alteram o percentual oficial.
- O mapa corporal do relatorio usa figura grande masculina/feminina e mostra baloes de medidas atuais/anteriores ao redor do corpo.
- Testes focados, lint, build, `specify check` e `git diff --check` passam antes do deploy.
