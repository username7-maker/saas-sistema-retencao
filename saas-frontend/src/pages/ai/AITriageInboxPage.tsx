import { PageHeader } from "../../components/ui";
import { WorkExecutionView } from "../../components/workQueue/WorkExecutionView";

export default function AITriageInboxPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Central Cordex"
        subtitle="Fila assistiva para preparar a proxima acao, sem explainability longa na frente da operacao."
      />

      <WorkExecutionView
        source="ai_triage"
        defaultDomain="all"
        title="Execucao da Central Cordex"
        subtitle="Abra o item, prepare a acao indicada, use a mensagem pronta e registre o resultado depois."
        compact
      />
    </div>
  );
}
