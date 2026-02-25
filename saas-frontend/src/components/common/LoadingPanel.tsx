export function LoadingPanel({ text = "Carregando dados..." }: { text?: string }) {
  return (
    <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-8 text-center text-lovable-ink-muted shadow-panel">
      <div className="mx-auto mb-4 flex w-full max-w-md flex-col gap-2 animate-pulse">
        <div className="h-3 w-full rounded bg-lovable-border" />
        <div className="h-3 w-4/5 rounded bg-lovable-border" />
        <div className="h-3 w-2/3 rounded bg-lovable-border" />
      </div>
      <p>{text}</p>
    </div>
  );
}
