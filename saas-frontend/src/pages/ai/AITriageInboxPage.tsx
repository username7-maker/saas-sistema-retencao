import { PageHeader } from "../../components/ui";
import { WorkExecutionView } from "../../components/workQueue/WorkExecutionView";

export default function AITriageInboxPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Inbox"
        subtitle="Fila assistiva para preparar a proxima acao, sem explainability longa na frente da operacao."
      />

      <WorkExecutionView
        source="ai_triage"
        title="Execucao da AI Inbox"
        subtitle="Abra o item, prepare a acao indicada, use a mensagem pronta e registre o resultado depois."
        compact
      />
    </div>
  );
}
