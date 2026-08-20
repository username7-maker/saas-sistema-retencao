# Spec 051 - Actuar Petroski Body Fat Parity + Body Map Assets

## Summary
Corrigir a Bioimpedancia v2 para que o protocolo `Petroski (1995), Homens, 18-66 anos` calcule gordura corporal com a mesma base operacional observada no Actuar para o caso de referencia enviado pelo usuario. Substituir o mapa corporal simplificado do relatorio por assets anatomicos genericos masculino/feminino, sem usar foto do aluno.

## Goals
- Ativar o protocolo Petroski masculino 4 dobras como calculo automatico quando as dobras obrigatorias estiverem presentes.
- Usar as dobras tricipital, subescapular, suprailiaca e panturrilha para o protocolo Petroski masculino.
- Validar o caso de referencia Actuar:
  - sexo masculino;
  - idade 22;
  - peso 73,60 kg;
  - altura 177 cm;
  - triceps 9 mm;
  - subescapular 12 mm;
  - suprailiaca 7 mm;
  - panturrilha 10 mm;
  - resultado esperado: 12,49% de gordura, 9,19 kg de massa de gordura, 64,41 kg de massa magra.
- Trocar o SVG interno do relatorio por imagem anatomica generica masculina/feminina.

## Non-goals
- Nao copiar layout, codigo, assets proprietarios ou logica proprietaria do Actuar.
- Nao alterar contrato de API, schema ou sync Actuar nesta correcao.
- Nao implementar todos os protocolos restantes nesta rodada.
- Nao substituir formulas de massa muscular ou dados brutos da bioimpedancia.
- Nao usar fotos de alunos.

## Acceptance Criteria
- Backend e frontend calculam Petroski masculino com 12,49% no caso de referencia.
- `body_fat_used_percent` continua sendo a fonte oficial quando o protocolo suportado e selecionado.
- O relatorio web mostra o mapa corporal masculino para sexo masculino e feminino para sexo feminino.
- A tabela de medidas corporais continua renderizando os dados atuais/anterior/variacao.
- Testes focados e build passam antes de publicar no piloto.

