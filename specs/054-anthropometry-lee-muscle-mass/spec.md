# Antropometria sem bioimpedancia: Slaughter, Lee e TMB

## Objetivo

Completar o Slaughter masculino, oferecer massa muscular esqueletica opcional pela equacao completa de Lee et al. (2000) em todos os protocolos e garantir TMB por Mifflin-St Jeor na avaliacao e no relatorio premium.

## Requisitos funcionais

- Slaughter masculino exige etnia branca ou negra e maturacao pre-pubere, pubere ou pos-pubere.
- O intercepto negro pre-pubere e `3.2`; somas acima de 35 mm usam o ramo linear publicado.
- `Calcular massa muscular` inicia desligado e, quando ligado, exige braco relaxado, coxa media, panturrilha maxima e as dobras tricipital, da coxa e da panturrilha do lado direito.
- Medidas compartilhadas com o protocolo sao reutilizadas e seguem a politica de duas tentativas, com terceira tentativa quando a tolerancia for excedida.
- Lee usa circunferencias corrigidas, sexo, idade, altura e etnia; menores de 18 anos e IMC maior ou igual a 30 recebem aviso de extrapolacao.
- TMB usa Mifflin-St Jeor para todas as avaliacoes sem bioimpedancia.
- O relatorio premium identifica massa muscular como estimativa antropometrica de Lee, mostra TMB em kcal/dia e diferencia massa muscular, massa livre de gordura e massa magra.

## Persistencia e compatibilidade

- `assessments.muscle_mass_kg` e nullable, positivo quando preenchido, e nao provoca backfill.
- O snapshot `anthropometry_snapshot_v2` registra escolhas, medidas, circunferencias corrigidas, formula, coeficientes, origem e flags metodologicas.
- As escolhas participam do hash do calculo e avaliacoes antigas continuam legiveis.

## Criterios de aceitacao

- Testes numericos cobrem sexo e coeficientes etnicos de Lee, conversao mm/cm e circunferencias corrigidas.
- Testes cobrem as seis combinacoes masculinas de Slaughter, inclusive negro pre-pubere `3.2`, e o ramo acima de 35 mm.
- A previa bloqueia dados obrigatorios ausentes, nao duplica campos e omite massa muscular quando a opcao esta desligada.
- TMB aparece na previa, persistencia e PDF; o PDF inclui origem e aviso de extrapolacao quando aplicavel.
