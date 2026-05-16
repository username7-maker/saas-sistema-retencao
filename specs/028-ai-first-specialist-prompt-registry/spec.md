# Spec 028 - AI First Specialist Prompt Registry

## User Story
Como gestor/professor, quero que os textos de IA sejam gerados por agentes especialistas por dominio, com modelo e prompt auditaveis, para confiar melhor nas recomendacoes sem perder revisao humana.

## Requirements
- O sistema deve ter registry backend de prompts versionados.
- `gpt-5.4-mini` deve ser o modelo padrao dos agentes especialistas.
- Outputs devem registrar `prompt_key`, `prompt_version`, `model`, `safety_profile` e `generated_at`.
- Bioimpedancia deve separar leitura para professor e aluno.
- Avaliacao deve usar prompt especialista.
- Personal IA, Aluno IA/Kommo, Agente Kommo e Video IA devem usar prompts especialistas e continuar supervisionados.
- OCR, safety, score, priorizacao e Work Queue devem permanecer determinísticos.

## Non-Goals
- Autoenvio.
- Prescricao autonoma.
- Diagnostico medico/biomecanico.
- Remocao de Claude.
