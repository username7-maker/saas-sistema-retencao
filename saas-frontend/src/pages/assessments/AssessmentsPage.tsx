import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Users } from "lucide-react";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";

import { AssessmentOperationsBoard } from "../../components/assessments/AssessmentOperationsBoard";
import type { AssessmentQueueFilter } from "../../components/assessments/assessmentOperationsUtils";
import { EmptyState, SkeletonList } from "../../components/ui";
import { Card, CardContent } from "../../components/ui2";
import { assessmentService, type AssessmentQueueResolutionStatus } from "../../services/assessmentService";

export function AssessmentsPage() {
  const queryClient = useQueryClient();
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

  const actuarQueueQuery = useQuery({
    queryKey: ["assessments", "actuar-sync-queue", searchQuery],
    queryFn: () => assessmentService.actuarSyncQueue({ search: searchQuery }),
    staleTime: 30 * 1000,
    placeholderData: (previousData) => previousData,
  });

  const queueResolutionMutation = useMutation({
    mutationFn: ({ memberId, status }: { memberId: string; status: AssessmentQueueResolutionStatus }) =>
      assessmentService.updateQueueResolution(memberId, { status }),
    onSuccess: (result) => {
      const successMessage = result.status === "active" ? "Pendencia reaberta na fila." : `${result.label} com sucesso.`;
      toast.success(successMessage);
      void queryClient.invalidateQueries({ queryKey: ["assessments"] });
    },
    onError: () => {
      toast.error("Nao foi possivel atualizar a pendencia de avaliacao.");
    },
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
    <div className="space-y-6">
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
        queueResolutionPendingMemberId={queueResolutionMutation.variables?.memberId ?? null}
        onQueueResolutionChange={(memberId, status) => {
          queueResolutionMutation.mutate({ memberId, status });
        }}
      />

      <Card>
        <CardContent className="space-y-4 pt-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-lovable-ink">Pendencias Actuar</p>
              <p className="text-xs text-lovable-ink-muted">Avaliacoes salvas que ainda nao estao prontas para treino no Actuar.</p>
            </div>
            {actuarQueueQuery.isFetching ? <span className="text-xs text-lovable-ink-muted">Atualizando...</span> : null}
          </div>

          {actuarQueueQuery.isLoading ? (
            <SkeletonList rows={4} cols={2} />
          ) : actuarQueueQuery.isError ? (
            <EmptyState
              icon={AlertTriangle}
              title="Nao foi possivel carregar as pendencias Actuar"
              description="Tente novamente para validar o status real de sincronizacao das avaliacoes."
              action={{ label: "Tentar novamente", onClick: () => void actuarQueueQuery.refetch() }}
            />
          ) : !actuarQueueQuery.data?.length ? (
            <p className="text-sm text-lovable-ink-muted">Sem pendencias Actuar no filtro atual.</p>
          ) : (
            <div className="space-y-3">
              {actuarQueueQuery.data.slice(0, 8).map((item) => (
                <div key={item.evaluation_id} className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <p className="font-semibold text-lovable-ink">{item.member_name}</p>
                      <p className="mt-1 text-xs text-lovable-ink-muted">
                        Avaliacao {new Date(`${item.evaluation_date}T12:00:00`).toLocaleDateString("pt-BR")} · Status {item.sync_status}
                      </p>
                      {item.error_code || item.error_message ? (
                        <p className="mt-2 text-xs text-lovable-danger">
                          {item.error_code ?? "erro"}{item.error_message ? ` · ${item.error_message}` : ""}
                        </p>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`rounded-full px-3 py-1 text-xs font-semibold ${item.training_ready ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"}`}>
                        {item.training_ready ? "Pronta" : "Nao pronta"}
                      </span>
                      <Link
                        to={`/assessments/members/${item.member_id}`}
                        className="inline-flex h-9 items-center justify-center rounded-lg border border-lovable-border px-3 text-xs font-semibold text-lovable-ink hover:bg-lovable-surface"
                      >
                        Abrir aluno
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
