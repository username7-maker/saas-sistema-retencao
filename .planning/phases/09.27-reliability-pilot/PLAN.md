# Confiabilidade, camera e mobile

Plano aprovado: preservar chaves de salvamento e isolar rascunhos por usuario,
academia e aluno; consolidar publicacao por SHA; preservar bordas do recibo e
permitir refazer segmentos; completar teclado/secoes mobile e indicadores de
atualizacao da retencao. Nenhuma formula ou avaliacao historica sera alterada.

Ordem: recuperacao e testes, camera, mobile/retencao, pipeline e piloto.
Validacao: testes focados e suites, lint/build, smoke autenticado, webcam fisica.
Estado inicial: c2712bc5; arquivo saas-backend/6 nao versionado preservado.
Estado: implementacao em andamento; nenhuma publicacao desta fase realizada.

Decisao de relatorio (15/09/2026): preservar os valores originais da
bioimpedancia e acrescentar sem sobrescrita historica a unidade percentual de
musculo esqueletico. IMC sera apresentado como calculado por peso e altura;
intervalo de incerteza da antropometria nao sera tratado como faixa clinica.
Para homens, gordura visceral usara a faixa operacional 1-12 solicitada pela
academia; para mulheres, permanece a faixa impressa no exame quando disponivel.
Nomes de fabricante ficam apenas em metadados tecnicos, e a interface publica
usa o termo bioimpedancia.

Decisao de score e procedencia (15/09/2026): o relatorio web deve consumir o
`origin_label` especifico devolvido pela API, preservando os fallbacks para
avaliacoes historicas. Componentes sem valor ou sem referencia clinica valida
nao entram no score; o total e normalizado para 0-100 apenas entre os
componentes realmente avaliaveis. Um valor ruim continua valendo zero e nao e
descartado da media. Essa regra evita penalizar o aluno por dado ausente ou por
uma classificacao que o sistema explicitamente nao pode sustentar.
