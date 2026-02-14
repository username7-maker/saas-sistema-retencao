export function LoadingPanel({ text = "Carregando dados..." }: { text?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-slate-500 shadow-panel animate-pulse">
      {text}
    </div>
  );
}
