import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";

import { memberTimelineService } from "../../services/memberTimelineService";
import type { Member } from "../../types";
import { MemberTimeline360Content } from "./MemberTimeline360Content";

interface MemberTimelineProps {
  member: Member;
  onClose: () => void;
}

export function MemberTimeline({ member, onClose }: MemberTimelineProps) {
  const query = useQuery({
    queryKey: ["member-timeline", member.id],
    queryFn: () => memberTimelineService.list(member.id),
    staleTime: 60 * 1000,
  });

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 px-4 py-8">
      <div className="relative max-h-[88vh] w-full max-w-6xl overflow-y-auto rounded-3xl border border-lovable-border bg-lovable-bg p-6 shadow-2xl">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 rounded-full border border-lovable-border bg-lovable-surface p-2 text-lovable-ink-muted hover:text-lovable-ink"
        >
          <X size={18} />
        </button>

        <MemberTimeline360Content member={member} events={query.data} isLoading={query.isLoading} isError={query.isError} />
      </div>
    </div>
  );
}
