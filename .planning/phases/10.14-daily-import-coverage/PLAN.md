# Importação diária Actuar: cobertura e confiabilidade

Contrato: avisar datas anteriores pendentes antes de importar arquivo posterior; exigir ciência explícita sem impedir recuperação de datas antigas. Base inicial: último acesso legado; daí em diante preservar âncora e dias completos no audit log da mesma transação. Não declarar completo arquivo com linhas rejeitadas. Dias sem acessos/academia fechada permanecem possíveis lacunas, não ausência comprovada. Nenhuma alteração de timestamps legados.

Implementar preview com datas, confirmação vinculada à lista atual, auditoria transacional, UI de confirmação e testes. Executar rotas de importação síncronas no thread pool do FastAPI: parsing, consultas e recálculo não devem bloquear o event loop. Preservar limites de upload, rate limits, permissões e tenant. Não repetir mutações automaticamente.

Investigar desempenho com evidência do código e logs sanitizados. Testar casos 11→13, recuperação de 12, arquivo sobreposto e lacuna interna, parcial, tenant, confirmação obsoleta e execução fora do event loop. Sem deploy nesta etapa até validação.
