import type { QueryClient } from "@tanstack/react-query";

export async function invalidateAssessmentQueries(queryClient: QueryClient, memberId: string): Promise<void> {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["assessments", "dashboard"] }),
    queryClient.invalidateQueries({ queryKey: ["assessments", "profile360", memberId] }),
    queryClient.invalidateQueries({ queryKey: ["assessments", "summary360", memberId] }),
    queryClient.invalidateQueries({ queryKey: ["assessments", "list", memberId] }),
    queryClient.invalidateQueries({ queryKey: ["assessments", "evolution", memberId] }),
    queryClient.invalidateQueries({ queryKey: ["body-composition", memberId] }),
    queryClient.invalidateQueries({ queryKey: ["member-timeline", memberId] }),
  ]);
}
