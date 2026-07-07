# STATUS - 09.18 Body Composition Anthropometry V1

Status: implementado localmente; aguardando revisao/publish do piloto.

## 2026-07-07

- Spec Kit aberta em `specs/049-body-composition-anthropometry-v1`.
- Fase GSD aberta em `.planning/phases/09.18-body-composition-anthropometry-v1`.
- Refinamentos obrigatorios incorporados antes do codigo:
  - `body_fat_percent` legado/bruto.
  - `body_fat_used_percent` oficial.
  - separacao calculo vs evolucao/perimetria.
  - GeneOS inconsistente exige revisao/override.
  - Actuar sem novos campos de perimetria na V1.
- Implementacao concluida no escopo local:
  - migration `20260707_0048_body_composition_anthropometry_v1`.
  - service de calculo Navy/RFM/GeneOS.
  - campos oficiais em modelo, schemas, relatorio, PDF, IA, WhatsApp/Kommo via payload oficial.
  - UI de medidas manuais/perimetria no fluxo de Bioimpedancia v2.
  - Actuar preservado com contrato legado sem perimetria nova.
- Lacunas contra o padrao Actuar reduzidas:
  - formulario agora mostra previa operacional antes de salvar.
  - relatorio web agora mostra painel de fonte oficial da gordura corporal.
  - revisao manual do percentual e revisao antropometrica ficaram visiveis na UI.
- Validacao visual adicionada:
  - e2e Playwright cobre relatorio com antropometria como fonte oficial.
  - screenshot salvo em `evidence/body-composition-report-source-panel.png`.
- Auditoria de paridade adicionada em `ACTUAR-PARITY-AUDIT.md`.
- Ajustes pos-auditoria:
  - `manual_override` agora persiste `measurement_source=manual_override`.
  - snapshot de IA pessoal removeu o campo legado ambiguo `body_fat_percent` e manteve `body_fat_used_percent` + `body_fat_bioimpedance_raw_percent`.
  - alertas/pills do fluxo Bioimpedancia v2 usam tokens dark-safe.
  - formulario ganhou checklist de protocolo e comparativo bilateral de perimetria antes de salvar.
