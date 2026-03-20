import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Users } from "lucide-react";

import { AssessmentOperationsBoard } from "../../components/assessments/AssessmentOperationsBoard";
import type { AssessmentQueueFilter } from "../../components/assessments/assessmentOperationsUtils";
import { EmptyState, SkeletonList } from "../../components/ui";
import { assessmentService } from "../../services/assessmentService";

export function AssessmentsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<AssessmentQueueFilter>("all");
  const [page, setPage] = useState(1);

  useEffect(() => {
    setPage(1);
  }, [activeFilter, searchQuery]);

  const dashboardQuery = useQuery({
    queryKey: ["assessments", "dashboard"],
    queryFn: () => assessmentService.dashboard(),
    staleTime: 5 * 60 * 1000,
  });

  const queueQuery = useQuery({
    queryKey: ["assessments", "queue", activeFilter, searchQuery, page],
    queryFn: () =>
      assessmentService.queue({
        page,
        page_size: 50,
        search: searchQuery,
        bucket: activeFilter,
      }),
    staleTime: 60 * 1000,
    placeholderData: (previousData) => previousData,
  });

  if (dashboardQuery.isLoading) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <div className="h-8 w-48 animate-pulse rounded-lg bg-lovable-border" />
          <div className="h-4 w-80 animate-pulse rounded-lg bg-lovable-border" />
        </div>
        <SkeletonList rows={8} cols={4} />
      </div>
    );
  }

  if (dashboardQuery.isError || !dashboardQuery.data) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Não foi possível carregar avaliações"
        description="Tente novamente para recuperar a fila operacional e os indicadores da base."
        action={{
          label: "Tentar novamente",
          onClick: () => {
            void dashboardQuery.refetch();
            void queueQuery.refetch();
          },
        }}
      />
    );
  }

  return (
    <AssessmentOperationsBoard
      dashboard={dashboardQuery.data}
      queue={queueQuery.data}
      queueLoading={queueQuery.isLoading}
      queueFetching={queueQuery.isFetching}
      queueError={queueQuery.isError}
      searchQuery={searchQuery}
      onSearchQueryChange={setSearchQuery}
      activeFilter={activeFilter}
      onActiveFilterChange={setActiveFilter}
      page={page}
      onPageChange={setPage}
      onClearFilters={() => {
        setSearchQuery("");
        setActiveFilter("all");
      }}
      onRetryQueue={() => {
        void queueQuery.refetch();
      }}
      emptyStateIcon={Users}
    />
  );
}
