# Plano

1. Criar modelo e migration para rotas Kommo por dominio e link membro-dominio.
2. Adicionar leitura/salvamento das rotas em Settings > Kommo.
3. Criar servico de link publico assinado para PDF de bioimpedancia.
4. Evoluir `kommo_service` para executar Salesbot com lead do dominio.
5. Criar endpoint generico `POST /api/v1/kommo/send-message`.
6. Alterar bioimpedancia para usar Salesbot e manter `Preparar na Kommo` como fallback.
7. Atualizar frontend de settings e botoes.
8. Validar tenant scope, build e testes focados.

## Principios
- Falhar de forma explicavel quando faltar rota, Salesbot, campo de mensagem/PDF, telefone ou URL publica.
- Nunca marcar como enviado se Salesbot nao foi executado.
- Registrar `MessageLog`, `AutopilotEvent` e auditoria.
- Nao cruzar tenants.
