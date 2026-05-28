# Retention OS

## 2026-05-20 - Retencao via canal principal
A regua de retencao deve produzir a acao e mensagem; o canal final e decidido pelo roteador. Para a ProGym, isso significa Kommo primeiro e WhatsApp apenas como fallback.

## Kommo
Retencao e reativacao devem usar o roteador de comunicacao. Quando Kommo for canal principal, a mensagem deve cair no pipeline/etapa de retencao e o Salesbot deve enviar ao numero oficial conectado, mantendo webhook para resposta e escalonamento.

## PDFs Operacionais
Quando uma acao operacional depender de arquivo, o padrao deve ser anexo nativo na Kommo. Links temporarios sao fallback explicito para contingencia, nao o caminho principal.

## Copy Agent
Retencao e reativacao devem usar rascunho especialista quando o contexto for seguro. Aluno 30+ dias recebe copy de reativacao, nao lembrete simples; base fria permanece campanha/fallback.

## Qualidade Tecnica
Retencao depende de jobs, migrations e IA confiaveis. A fase 09.5 corrige o default do modelo especialista e endurece o CI para reduzir risco de regressao silenciosa em automacoes, filas e mensagens.
# 2026-05-21 - Interface como Command Center

Retencao continua sendo o eixo operacional, mas a experiencia visual passa a posicionar o Cordex como centro de comando: riscos, acoes, briefing e indicadores devem aparecer com hierarquia de decisao, nao como tela administrativa comum.
