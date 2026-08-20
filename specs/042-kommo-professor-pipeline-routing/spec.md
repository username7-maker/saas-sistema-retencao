# Spec 042 - Kommo Professor Pipeline Routing

## User Story
Como gestor da Cordex, quero que a Kommo possa rotear acoes tecnicas para a pipeline do professor responsavel pelo aluno, sem depender do nome da pipeline e sem alterar o roteamento por dominio das outras operacoes.

## Requirements
- O trabalho deve seguir GSD, Spec Kit e registro Obsidian.
- O Cordex deve salvar rotas Kommo por professor usando IDs operacionais, nunca nomes de pipeline como chave.
- A rota por professor se aplica apenas a dominios tecnicos: `assessment`, `body_composition`, `student_ai` e acoes internas `trainer` normalizadas para tecnico.
- Para dominios nao tecnicos (`retention`, `onboarding`, `finance`, `sales`, `support`), o comportamento por dominio deve permanecer igual.
- Quando uma acao tecnica tiver aluno com `member.assigned_user_id`, o resolvedor deve tentar uma rota ativa e completa para esse professor.
- Quando a rota do professor estiver ausente, desativada ou incompleta, o envio deve cair na rota de dominio existente como fallback de coordenacao.
- O vinculo `KommoMemberDomainLink` deve ser preservado por dominio para evitar leads duplicados.
- Se o aluno trocar de professor, o proximo envio tecnico deve mover o lead existente para pipeline/stage/responsavel resolvidos.
- Settings Kommo deve ler e salvar `trainer_routes` junto com `domain_routes`.
- A tela Configuracoes > Kommo deve listar professores ativos e mostrar status `Pronto`, `Incompleto` ou `Desativado`.
- Logs e resultados devem expor `trainer_route`, `coordination_fallback` ou `domain_route`, sem vazar token nem payload sensivel.

## Non-Goals
- Criar pipelines automaticamente na Kommo.
- Usar nomes de professores/pipelines como identificador operacional.
- Alterar rotas de retencao, onboarding, financeiro, comercial ou suporte.
- Remover o fallback por dominio existente.
- Ativar automacoes destrutivas novas.

## Acceptance Criteria
- `specify check` passa antes e depois.
- Migration cria `kommo_trainer_routes` com unicidade por `gym_id + trainer_user_id`.
- `GET /api/v1/settings/kommo` retorna `trainer_routes` para professores ativos.
- `PUT /api/v1/settings/kommo` salva rotas por professor e rejeita professor fora da academia ou sem papel `trainer`.
- Resolvedor usa `trainer_route` em acao tecnica quando ha professor com rota completa.
- Resolvedor usa `coordination_fallback` quando nao ha professor ou rota completa.
- Dominios nao tecnicos continuam usando `domain_route`.
- Envio para lead existente usa PATCH para mover pipeline/stage/responsavel resolvidos.
- UI mostra "Pipelines por professor", permite editar IDs e salva `trainer_routes`.
- Testes backend e frontend focados cobrem os cenarios principais.
