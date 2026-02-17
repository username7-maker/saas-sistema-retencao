import clsx from "clsx";

interface SkeletonCardProps {
  variant?: "stat" | "chart" | "list";
  className?: string;
}

export function SkeletonCard({ variant = "stat", className }: SkeletonCardProps) {
  if (variant === "stat") {
    return (
      <div className={clsx("animate-pulse rounded-2xl bg-slate-200 p-5", className)}>
        <div className="h-3 w-20 rounded bg-slate-300" />
        <div className="mt-4 h-8 w-24 rounded bg-slate-300" />
      </div>
    );
  }

  if (variant === "chart") {
    return (
      <div className={clsx("animate-pulse rounded-2xl border border-slate-200 bg-white p-4", className)}>
        <div className="h-4 w-32 rounded bg-slate-200" />
        <div className="mt-4 flex items-end gap-2">
          {[40, 65, 45, 80, 55, 70, 60].map((h, i) => (
            <div key={i} className="flex-1 rounded-t bg-slate-200" style={{ height: `${h}%`, minHeight: h }} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={clsx("animate-pulse rounded-2xl border border-slate-200 bg-white p-4", className)}>
      <div className="h-4 w-40 rounded bg-slate-200" />
      <div className="mt-4 space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-slate-200" />
            <div className="flex-1 space-y-1">
              <div className="h-3 w-3/4 rounded bg-slate-200" />
              <div className="h-2 w-1/2 rounded bg-slate-100" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <section className="space-y-6">
      <div className="space-y-1">
        <div className="h-8 w-64 animate-pulse rounded bg-slate-200" />
        <div className="h-4 w-96 animate-pulse rounded bg-slate-100" />
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {[1, 2, 3, 4, 5].map((i) => (
          <SkeletonCard key={i} variant="stat" />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <SkeletonCard variant="chart" className="h-64" />
        <SkeletonCard variant="chart" className="h-64" />
      </div>
    </section>
  );
}
