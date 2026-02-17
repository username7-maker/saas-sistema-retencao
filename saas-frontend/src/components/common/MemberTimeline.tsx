import { useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, Star, Clipboard, Zap, X } from "lucide-react";
import clsx from "clsx";

import { api } from "../../services/api";
import type { Member } from "../../types";

interface TimelineEvent {
  type: string;
  timestamp: string;
  title: string;
  detail: string;
  icon: string;
  level?: string;
}

interface MemberTimelineProps {
  member: Member;
  onClose: () => void;
}

const iconMap: Record<string, React.ComponentType<{ size: number; className?: string }>> = {
  activity: Activity,
  "alert-triangle": AlertTriangle,
  star: Star,
  clipboard: Clipboard,
  zap: Zap,
};

const typeColors: Record<string, string> = {
  checkin: "border-emerald-300 bg-emerald-50",
  risk_alert: "border-rose-300 bg-rose-50",
  nps: "border-amber-300 bg-amber-50",
  task: "border-violet-300 bg-violet-50",
  automation: "border-blue-300 bg-blue-50",
};

const iconColors: Record<string, string> = {
  checkin: "text-emerald-500",
  risk_alert: "text-rose-500",
  nps: "text-amber-500",
  task: "text-violet-500",
  automation: "text-blue-500",
};

export function MemberTimeline({ member, onClose }: MemberTimelineProps) {
  const query = useQuery({
    queryKey: ["member-timeline", member.id],
    queryFn: async () => {
      const { data } = await api.get<TimelineEvent[]>(`/api/v1/members/${member.id}/timeline`);
      return data;
    },
    staleTime: 60 * 1000,
  });

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 pt-12">
      <div className="relative max-h-[80vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 text-slate-400 hover:text-slate-600"
        >
          <X size={20} />
        </button>

        <header className="mb-4">
          <h3 className="font-heading text-xl font-bold text-slate-900">{member.full_name}</h3>
          <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
            <span>{member.plan_name}</span>
            <span>|</span>
            <span>R$ {member.monthly_fee.toFixed(2)}/mes</span>
            <span>|</span>
            <span className={clsx(
              "font-semibold",
              member.risk_level === "red" && "text-rose-600",
              member.risk_level === "yellow" && "text-amber-600",
              member.risk_level === "green" && "text-emerald-600",
            )}>
              Risco: {member.risk_level.toUpperCase()} ({member.risk_score})
            </span>
          </div>
        </header>

        <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Timeline</h4>

        {query.isLoading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse rounded-lg border border-slate-200 p-3">
                <div className="h-3 w-32 rounded bg-slate-200" />
                <div className="mt-2 h-2 w-48 rounded bg-slate-100" />
              </div>
            ))}
          </div>
        )}

        {query.data && query.data.length === 0 && (
          <p className="text-sm text-slate-400">Nenhum evento registrado.</p>
        )}

        {query.data && query.data.length > 0 && (
          <div className="relative space-y-3 pl-6 before:absolute before:left-2 before:top-0 before:h-full before:w-px before:bg-slate-200">
            {query.data.map((event, idx) => {
              const IconComponent = iconMap[event.icon] ?? Activity;
              return (
                <div
                  key={idx}
                  className={clsx(
                    "relative rounded-lg border p-3",
                    typeColors[event.type] ?? "border-slate-200 bg-slate-50",
                  )}
                >
                  <div className="absolute -left-[22px] top-3 flex h-5 w-5 items-center justify-center rounded-full bg-white shadow-sm">
                    <IconComponent size={12} className={iconColors[event.type] ?? "text-slate-400"} />
                  </div>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium text-slate-700">{event.title}</p>
                      {event.detail && <p className="text-xs text-slate-500">{event.detail}</p>}
                    </div>
                    <time className="shrink-0 text-[10px] text-slate-400">
                      {new Date(event.timestamp).toLocaleDateString("pt-BR", {
                        day: "2-digit",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </time>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
