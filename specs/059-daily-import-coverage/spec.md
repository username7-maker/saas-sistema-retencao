# Cobertura diária de importações

Na importação de check-ins da Actuar, o operador recebe os dias sem cobertura confirmada até o último dia do arquivo, a partir de uma âncora conhecida. Aceitar dias anteriores e arquivos sobrepostos; duplicatas não contam como falha. Apenas arquivos sem erros registram seus dias observados como completos. Avisos exigem confirmação explícita para a lista atual; nova lacuna exige revalidação. Não inventar cobertura de datas sem linhas ou histórico anterior à âncora. Dados e cobertura confirmada devem ser persistidos na mesma transação por academia.

Processamento de arquivos e SQL síncronos não ocupam o event loop da API. Nenhuma mudança em identidade, fórmulas de risco, APIs externas ou relógio histórico de check-ins.
