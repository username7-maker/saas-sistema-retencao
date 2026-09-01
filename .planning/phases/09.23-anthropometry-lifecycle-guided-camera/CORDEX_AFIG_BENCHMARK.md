# Benchmark técnico de produto: Cordex × AFIG

Data da revisão: 2026-09-01

## Escopo e método

Esta análise compara maturidade de produto e desenvolvimento. Ela não compara avaliações de alunos, não valida equivalência numérica entre métodos e não tenta reproduzir código ou fórmulas proprietárias do AFIG.

Evidências externas utilizadas:

- [Página oficial do AFIG](https://afig.actuar.com/): declara acesso web/multiplataforma, relatório on-line, envio por e-mail/SMS, agenda, anamnese, resistência, composição corporal, flexibilidade, protocolos, VO₂ e perimetria.
- [Trilha oficial de treinamento do AFIG](https://treinamento.actuar.com/tv_shows/afig/): organiza seis módulos — anamnese; composição e perimetria; força e resistência; flexibilidade; capacidade aeróbica; relatórios.

O Cordex foi avaliado pelo código, testes e telas desta versão. Capacidades internas do AFIG que não são demonstradas publicamente foram classificadas como `não verificável`.

## Matriz funcional e de maturidade

| Dimensão | Cordex atual | AFIG verificável | Classificação | Evidência e leitura de desenvolvimento |
|---|---|---|---|---|
| Criação de composição/perimetria | Formulário integrado ao perfil, prévia antes de salvar e 32 protocolos calculáveis | Módulo específico de composição/perimetria | Equivalente | Ambos cobrem o fluxo principal; Cordex explicita prévia e origem no domínio atual. |
| Seleção por sexo, idade e população | Regras de elegibilidade no catálogo e backend | “Dezenas de protocolos” | Cordex superior | No Cordex as restrições são validadas pelo servidor e testadas em matriz; os detalhes do AFIG não são públicos. |
| Composição corporal | IMC, gordura, massas, TMB e massa muscular quando elegível | IMC, gordura, massa magra e outros | Equivalente | Paridade funcional no núcleo anunciado publicamente. |
| Perimetria | Tentativas, consolidação, lados, mapa corporal e evolução | Perímetros e cálculo de massa muscular | Equivalente | Cordex guarda evidência das tentativas; funcionamento interno do AFIG não é verificável. |
| Transparência de fórmula/origem | Fórmula, versão, hash e origem por indicador | Não divulgado publicamente | Cordex superior | Rastreabilidade é um diferencial explícito do Cordex. |
| Histórico e evolução | Histórico unificado, comparação somente entre métodos compatíveis | Histórico é demonstrado no módulo/relatórios | Equivalente | Cordex evita tratar antropometria e bioimpedância como métodos equivalentes. |
| Relatório web/PDF/impressão | Apresentação web premium, PDF autenticado e impressão | Relatório on-line, impressão e envio por e-mail/SMS | Cordex parcialmente implementado | O relatório está equivalente; compartilhamento direto multicanal ainda é menor. |
| Edição/exclusão/recuperação | Edição com controle concorrente, exclusão lógica, auditoria e recuperação técnica | Não verificável publicamente | Cordex superior | O AFIG não publica comportamento de concorrência ou recuperação. |
| Prevenção de erros | Limites plausíveis, tentativas, requisitos do protocolo, cálculo central | Não verificável publicamente | Cordex superior | Cobertura do Cordex é verificável por testes; não há evidência comparável do AFIG. |
| Experiência mobile | Layout responsivo e scanner guiado | Declara celular/tablet/computador | Cordex parcialmente implementado | Scanner foi projetado para mobile; validação final ainda exige matriz real Android/iOS. |
| Anamnese/PAR-Q/AHA | Contexto clínico parcial, sem módulo físico dedicado equivalente | Módulo anunciado e treinamento próprio | Ausente no Cordex | Lacuna funcional relevante, mas fora dos P0 desta fase. |
| Força e resistência | Campos/indicadores parciais, sem jornada completa equivalente | Módulo específico | Cordex parcialmente implementado | Exige desenho de produto separado. |
| Flexibilidade | Indicador parcial, sem protocolo visual completo | Módulo com auxílio de imagens | Cordex parcialmente implementado | Exige catálogo, evidência e relatório próprios. |
| Capacidade aeróbica/VO₂ | Campo estimado parcial | Módulo com vários protocolos | Cordex parcialmente implementado | Não deve ser ampliado sem validação de protocolos. |
| Agenda de avaliações | Datas futuras e tarefas operacionais | Agenda e notificações declaradas | Cordex parcialmente implementado | Cordex tem automação operacional, mas não uma agenda dedicada equivalente. |
| Permissões, auditoria e isolamento | RBAC, tenant por academia e eventos de auditoria | Segurança/backups declarados; detalhes não públicos | Cordex superior | A classificação considera recursos verificáveis, não uma auditoria de segurança do AFIG. |
| Integração com gestão/Actuar | Integração controlada; antropometria exige confirmação manual | Produto do ecossistema Actuar | Cordex parcialmente implementado | AFIG tem vantagem natural de ecossistema; Cordex preserva segurança ao não simular sincronização. |
| Arquitetura, desempenho e manutenção | Frontend/API/worker versionados, testes e rollout por SHA | Não verificável publicamente | Não verificável | Não há evidência pública suficiente sobre arquitetura interna do AFIG. |
| Acessibilidade | Controles rotulados e navegação web parcial | Não verificável publicamente | Cordex parcialmente implementado | Ainda falta auditoria WCAG completa no Cordex. |

## Backlog priorizado

### P0 — fluxo atual

1. Apresentação web premium para antropometria após salvar.
2. Edição integral com recomputação no backend e conflito `409`.
3. Exclusão lógica restrita, auditoria e preservação de tarefas concluídas.
4. Correção de datas ISO completas, datas simples e legado inválido.
5. Scanner guiado com câmera traseira, troca de dispositivo, recorte, rotação, compressão e avisos locais.

### P1 — paridade relevante

1. Compartilhamento controlado do relatório antropométrico por canal autorizado.
2. Agenda dedicada de avaliações sobre as tarefas e datas já existentes.
3. Auditoria de acessibilidade WCAG e testes reais em Safari iOS/Chrome Android.
4. Recuperação administrativa visível de avaliações excluídas, com justificativa e trilha.
5. Biblioteca de ajuda contextual para pontos anatômicos e protocolo selecionado.

### P2 — módulos futuros

1. Anamnese estruturada, PAR-Q e instrumentos aplicáveis, após revisão jurídica/clínica.
2. Força e resistência muscular com protocolos e progressão próprios.
3. Flexibilidade com instruções visuais e referências validadas.
4. Capacidade aeróbica/VO₂ com protocolos, contraindicações e relatório específico.
5. Jornada integrada de agenda, avaliação, prescrição e comunicação.

## Riscos e recomendações

| Lacuna | Impacto | Complexidade | Risco | Recomendação |
|---|---|---:|---|---|
| Mobile sem validação física ampla | Foto ruim e abandono do professor | Média | Operacional | Homologar aparelhos reais antes de declarar suporte completo. |
| Sincronização antropométrica manual | Divergência Cordex/Actuar | Média | Operacional | Manter tarefa pendente explícita; automatizar somente com API oficial ou integração autorizada confiável. |
| Módulos clínicos ausentes | Menor paridade comercial | Alta | Clínico | Tratar cada módulo como fase independente com fontes, limites e testes próprios. |
| Recuperação só técnica | Owner depende de suporte | Média | Governança | Criar painel de restauração com permissão forte e auditoria em P1. |
| Compartilhamento menor | Mais passos para entregar resultado | Média | Privacidade | Implementar consentimento, expiração e log antes de ampliar canais. |

## Conclusão

No núcleo de composição corporal e perimetria, o Cordex alcança paridade funcional e supera o que é publicamente verificável em transparência de cálculo, auditoria e prevenção de sobrescrita. O AFIG permanece mais amplo como suíte de avaliação física por reunir anamnese, testes físicos, flexibilidade, VO₂ e agenda. Esses módulos não devem ser copiados para esta fase: formam um roadmap separado, com validação clínica e operacional própria.
