# Plan 042 - Kommo Professor Pipeline Routing

## Context
A Kommo ja e o canal operacional universal para automacoes supervisionadas. Ate agora o Cordex resolve envio por dominio, mas a operacao tecnica quer uma pipeline por professor. O Cordex deve continuar dono das regras e salvar apenas IDs configurados.

## Backend
1. Criar `KommoTrainerRoute` com os mesmos campos operacionais de `KommoDomainRoute`, usando chave unica `gym_id + trainer_user_id`.
2. Adicionar migration Alembic para a tabela e indices.
3. Adicionar schemas `KommoTrainerRouteRead` e `KommoTrainerRouteUpdate`.
4. Estender o service de settings para serializar professores ativos e salvar rotas.
5. Criar resolvedor unico para envios de aluno:
   - normalizar `trainer`/`coach` para dominio tecnico `assessment`;
   - tentar rota do professor para dominios tecnicos;
   - cair para rota de dominio como fallback de coordenacao;
   - manter dominios nao tecnicos por dominio.
6. Adicionar `route_kind`, `trainer_user_id` e `route_fallback_reason` em resultados/logs/eventos.

## Frontend
1. Adicionar tipos `KommoTrainerRoute` e `trainer_routes`.
2. Estender `KommoConnectionTab` com secao "Pipelines por professor".
3. Mostrar status visual sem bloquear operacao quando rota esta incompleta.
4. Enviar `trainer_routes` no payload de salvamento.

## Tests
- Backend settings service/router.
- Backend resolver Kommo.
- Frontend Kommo settings.
- Validacao final: Spec Kit, testes focados, lint/build e smoke no piloto.

## Rollout
Publicar no piloto apos validacao local. As rotas ficam configuraveis, mas nenhuma automacao destrutiva nova e ativada por esta fase.
