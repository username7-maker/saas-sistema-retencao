import clsx from "clsx";

interface StatCardProps {
  label: string;
  value: string;
  tone?: "neutral" | "success" | "warning" | "danger";
}

const toneStyles: Record<NonNullable<StatCardProps["tone"]>, string> = {
  neutral: "from-slate-900 to-slate-800",
  success: "from-brand-700 to-brand-500",
  warning: "from-amber-600 to-amber-500",
  danger: "from-rose-700 to-rose-500",
};

export function StatCard({ label, value, tone = "neutral" }: StatCardProps) {
  return (
    <article
      className={clsx(
        "rounded-2xl bg-gradient-to-br p-5 text-white shadow-panel transition hover:-translate-y-1",
        toneStyles[tone],
      )}
    >
      <p className="text-xs uppercase tracking-[0.2em] text-white/70">{label}</p>
      <p className="mt-3 text-3xl font-heading font-bold">{value}</p>
    </article>
  );
}
