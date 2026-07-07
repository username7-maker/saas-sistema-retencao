# Decisions

## 2026-07-07 - Protocolos Antropometricos Como Catalogo Seguro
O Cordex pode listar os protocolos operacionais usados pela academia, mas so calcula automaticamente protocolos de dobras cutaneas com formula publica implementada e campos obrigatorios presentes. Protocolos sem formula validada em V1 permanecem como catalogo/manual review e nao podem alterar `body_fat_used_percent` sem override/revisao explicita. O relatorio ganha um mapa corporal proprio e neutro para perimetria, sem copiar layout do Actuar.

## 2026-07-07 - Percentual Oficial por Medidas
Para Bioimpedancia v2, `body_fat_percent` deixa de ser fonte oficial e fica como campo bruto/legado de bioimpedancia, OCR, compatibilidade e Actuar. O produto deve usar `body_fat_used_percent` em cards principais, relatorio web, PDF, IA, WhatsApp e Kommo. Antropometria entra no fluxo existente, sem copiar Actuar, sem modulo paralelo, sem diagnostico clinico e sem usar bracos, coxas, panturrilhas, torax ou ombros como entrada direta do calculo de gordura.

Complemento: `manual_override` e uma fonte explicita e rastreavel, nao uma variacao silenciosa de antropometria. Snapshots de IA devem expor `body_fat_used_percent` e `body_fat_bioimpedance_raw_percent`, mas nao devem apresentar `body_fat_percent` como campo generico.

## 2026-06-22 - Bioimpedancia: relatorio primeiro, sem novo modulo
A referencia do video/comprovante deve alimentar o relatorio de bioimpedancia existente com campos reais do exame. Nao criar uma nova superficie de leitura estrategica para esta correcao; qualquer evolucao de IA para avaliacao fisica precisa de escopo proprio e revisao antes de entrar na UI.

## 2026-05-28 - Avatar Upload V1 Usa Persistencia Em Banco
Para a Phase 4.35, o caminho principal de avatar passa a ser upload de arquivo multipart. Na V1, o arquivo continua persistido como data URL em `users.avatar_url`, porque o piloto nao tem object storage nem volume persistente dedicado para uploads da API. URL manual permanece apenas como compatibilidade/fallback, nao como experiencia principal.

## 2026-05-27 - Relatorios Mensais Tenant-Scoped
O disparo mensal de relatorios deve usar o `gym_id` do job como limite operacional para destinatarios. Mesmo que o worker rode fora do request HTTP, o envio so pode buscar OWNER/MANAGER da academia relacionada ao job. Qualquer consolidado cross-tenant precisa de fase propria e contrato explicito.

## 2026-05-27 - Resend como Provedor de Email Transacional
O Cordex Gym OS passa a usar Resend para e-mails transacionais. `SENDGRID_*` deixa de ser superficie ativa; o backend usa `RESEND_API_KEY` somente por ambiente seguro e `RESEND_SENDER` como remetente configuravel. Enquanto `cordex.com` nao estiver verificado no Resend, o remetente de teste deve ser `Cordex Gym OS <onboarding@resend.dev>` com `RESEND_REPLY_TO=automai904@gmail.com`. Chaves coladas em chat devem ser rotacionadas antes de producao.

## 2026-05-27 - Retencao como Superficie de Acao Compacta
O drawer de retencao passa a priorizar leitura e execucao: sinais compactos, playbook mais escaneavel e barra fixa de acoes principais. Cordex Coach e Video de Movimento ficam ocultos apenas no Perfil 360 nesta V1, sem remover services, settings ou rotas globais.

## 2026-05-27 - Kommo Pipeline por Professor Somente Tecnico
Kommo passa a suportar rota por professor para dominios tecnicos (`assessment`, `body_composition`, `student_ai` e alias interno `trainer`). O Cordex salva IDs por professor em `kommo_trainer_routes`, nunca nomes de pipeline. Retencao, onboarding, financeiro, comercial e suporte continuam por dominio. Se o aluno nao tem professor ou a rota do professor esta desativada/incompleta, o envio cai na rota de dominio como fallback de coordenacao.

## 2026-05-15 - Kommo Salesbot por Dominio
Kommo usa `salesbot_outbound` para envio operacional real. "Abas" da Kommo serao pipeline/etapa/tag por dominio. `handoff_task` permanece como fallback legado quando rota, Salesbot ou PDF nao estiverem prontos.

## 2026-05-15 - PDF Kommo Nativo
PDF via Kommo deve ser upload/anexo nativo quando a rota exigir documento. `pdf_url` temporario permanece como fallback explicito, nao como sucesso principal da bioimpedancia.

## 2026-05-19 - Copy Agent Supervisionado
Mensagens operacionais podem ser melhoradas por agente especialista em modo rascunho. Safety vence copywriting: sensiveis, VIP, opt-out e disputas ficam com humano/template seguro.

## 2026-05-20 - Kommo Canal Universal
Toda automacao de mensagem deve resolver o canal pelo tenant. Quando `primary_message_channel=kommo`, Kommo/Salesbot e o caminho preferencial; WhatsApp permanece fallback auditavel.

## 2026-05-20 - Quality Hardening
`OPENAI_SPECIALIST_MODEL` usa `gpt-4.1-mini` por default; `gpt-5.4-mini` foi removido por nao ser modelo valido na API. CI deve bloquear mypy/pip-audit, e migrations Alembic nao devem manter branches redundantes.
# 2026-05-21 - Cordex Command Center como padrao visual premium

Decisao: Cordex Command Center e o padrao visual premium do frontend. A entrega sera feita em ondas para preservar a operacao real: primeiro design system, app shell e dashboards; depois paginas operacionais profundas.

Motivo: o produto precisa transmitir alto valor percebido sem quebrar Work Queue, avaliacoes, Kommo, onboarding, retencao e demais fluxos ativos no piloto.
