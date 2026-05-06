# Validacao

## Cenários obrigatorios

1. Aluno ativo com check-in recente
   - perfil mostra sinais positivos
   - next best action nao cria contato de retencao desnecessario

2. Aluno 14+ dias sem check-in
   - perfil mostra risco/retencao como dominio prioritario
   - acao recomendada aponta responsavel correto
   - evidencias explicam dias sem check-in e tentativas anteriores

3. Aluno com avaliacao recente
   - perfil mostra regua tecnica pos-avaliacao
   - task D+8/D+14/D+90 aparece na esteira quando existir

4. Aluno com pendencia financeira
   - owner/manager veem resumo financeiro
   - trainer nao ve dado financeiro sensivel

5. Aluno com mensagem sensivel
   - next best action prioriza intervencao humana
   - Autopilot aparece bloqueado/escalado, nao como sucesso simples

6. Perfil por role
   - owner/manager veem completo
   - receptionist ve operacao sem clinico profundo
   - trainer ve tecnico sem financeiro/comercial sensivel
   - salesperson ve comercial sem saude detalhada

## Gates tecnicos

- [x] Testes backend de permissao por role.
- [ ] Testes backend de tenant isolation e next best action.
- [ ] Testes frontend de renderizacao do snapshot e fallback de blocos.
- [x] `npm.cmd run build`.
- [x] `python -m compileall saas-backend/app`.
- Smoke autenticado no piloto com pelo menos 3 alunos reais.

## Resultado tecnico desta rodada

- Backend compilou sem erro.
- Frontend buildou com `tsc -b && vite build`.
- Regressao focada passou: `12 passed`.
- Migration head unico: `20260505_0039`.
