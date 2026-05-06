# Validacao

## Cenários de aceite

- Bioimpedancia salva cria ou atualiza as tarefas `assessment_training_delivery_check_d8`, `assessment_feedback_followup` e `assessment_reassessment_due`.
- Avaliacao formal continua criando as mesmas tres tarefas.
- Formal + bioimpedancia no mesmo ciclo tecnico nao duplicam tarefas abertas.
- Bioimpedancia remove aluno da condicao de "nenhuma avaliacao registrada".
- `Salvar apenas no sistema` nao cria tentativa de sync Actuar.
- `Salvar e enviar ao Actuar` mantem o comportamento atual de sync.
- Professor nao recebe `Agendar primeira avaliacao`.
- Professor recebe apenas tarefas tecnicas pos-avaliacao/bioimpedancia.
- Relatorio premium renderiza logo ProGym ao lado de `AI Gym OS`.

## Comandos sugeridos

```powershell
python -m pytest saas-backend/tests/test_body_composition.py saas-backend/tests/test_onboarding_score.py saas-backend/tests/test_work_queue_service.py saas-backend/tests/test_report_service.py -q
npm.cmd run build
specify check
```

## Resultado local

- PASS: `python -m compileall saas-backend\app`
- PASS: `specify check`
- PASS: `python -m pytest saas-backend\tests\test_assessment_service.py saas-backend\tests\test_body_composition.py saas-backend\tests\test_onboarding_score.py saas-backend\tests\test_work_queue_service.py saas-backend\tests\test_report_service.py -q` (`71 passed`)
- PASS: `npm.cmd run build`
- PASS: `npm.cmd test -- MemberBodyCompositionTab.test.tsx`
