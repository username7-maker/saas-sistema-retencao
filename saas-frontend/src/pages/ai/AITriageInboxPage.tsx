import { WorkExecutionView } from "../../components/workQueue/WorkExecutionView";

export default function AITriageInboxPage() {
  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden rounded-[18px] border border-[rgba(139,92,246,0.28)] bg-[radial-gradient(ellipse_70%_55%_at_85%_10%,rgba(139,92,246,0.10),transparent_65%),linear-gradient(145deg,rgba(14,16,24,0.97),rgba(10,11,15,0.96))] p-5 shadow-card backdrop-blur-xl">
        <p className="text-[11px] font-bold uppercase tracking-[0.3em] text-violet-400">IA · Cordex</p>
        <h2 className="mt-1 font-heading text-3xl font-bold md:text-4xl">
          <span className="bg-gradient-to-r from-white via-white to-violet-300 bg-clip-text text-transparent">Central Cordex</span>
        </h2>
        <p className="mt-1 text-sm text-lovable-ink-muted">Fila assistiva para preparar a próxima ação, sem explainability longa na frente da operação.</p>
      </div>

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
