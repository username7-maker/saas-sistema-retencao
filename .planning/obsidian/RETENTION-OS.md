# Retention OS

## Kommo
Retencao e reativacao devem usar o roteador de comunicacao. Quando Kommo for canal principal, a mensagem deve cair no pipeline/etapa de retencao e o Salesbot deve enviar ao numero oficial conectado, mantendo webhook para resposta e escalonamento.

## PDFs Operacionais
Quando uma acao operacional depender de arquivo, o padrao deve ser anexo nativo na Kommo. Links temporarios sao fallback explicito para contingencia, nao o caminho principal.
