import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CalendarDays, Users } from "lucide-react";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";

import { AssessmentOperationsBoard } from "../../components/assessments/AssessmentOperationsBoard";
import type { AssessmentQueueFilter, PreferredShiftFilter } from "../../components/assessments/assessmentOperationsUtils";
import { EmptyState, SkeletonList } from "../../components/ui";
import { Card, CardContent } from "../../components/ui2";
import {
  assessmentService,
  type AssessmentAppointment,
  type AssessmentQueueResolutionStatus,
} from "../../services/assessmentService";

type AssessmentWorkspaceView = "queue" | "agenda";

function toDateInputValue(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function addDays(date: Date, days: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function formatDateTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "-";
  return parsed.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getAppointmentStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    scheduled: "Agendada",
    confirmed: "Confirmada",
    attended: "Compareceu",
    no_show: "Faltou",
    cancelled: "Cancelada",
    rescheduled: "Remarcada",
    completed: "Concluida",
  };
  return labels[status] ?? status;
}

function getPaymentStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    unknown: "Pagamento nao informado",
    pending: "Pagamento pendente",
    paid: "Pago",
    waived: "Isento",
    not_required: "Nao requerido",
  };
  return labels[status] ?? status;
}

function AssessmentAgendaPanel({
  appointments,
  isLoading,
  isFetching,
  isError,
  dateFrom,
  dateTo,
  status,
  paymentStatus,
  searchQuery,
  onDateFromChange,
  onDateToChange,
  onStatusChange,
  onPaymentStatusChange,
  onSearchQueryChange,
  onRetry,
  onUpdateAppointment,
  updatingAppointmentId,
}: {
  appointments: AssessmentAppointment[];
  isLoading: boolean;
  isFetching: boolean;
  isError: boolean;
  dateFrom: string;
  dateTo: string;
  status: string;
  paymentStatus: string;
  searchQuery: string;
  onDateFromChange: (value: string) => void;
  onDateToChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  onPaymentStatusChange: (value: string) => void;
  onSearchQueryChange: (value: string) => void;
  onRetry: () => void;
  onUpdateAppointment: (id: string, payload: Partial<AssessmentAppointment>) => void;
  updatingAppointmentId?: string | null;
}) {
  return (
    <Card>
      <CardContent className="space-y-4 pt-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Agenda de avaliacoes</p>
            <h2 className="mt-1 text-2xl font-bold text-lovable-ink">Planilha Excel operacional</h2>
            <p className="mt-1 max-w-3xl text-sm text-lovable-ink-muted">
              Use esta agenda para acompanhar horario, professor, comparecimento e pagamento. Compareceu/concluiu conta como historico,
              mas nao cria avaliacao tecnica sem medidas.
            </p>
          </div>
          {isFetching && !isLoading ? <span className="text-xs text-lovable-ink-muted">Atualizando...</span> : null}
        </div>

        <div className="grid gap-3 md:grid-cols-5">
          <input
            type="date"
            value={dateFrom}
            onChange={(event) => onDateFromChange(event.target.value)}
            className="rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink"
          />
          <input
            type="date"
            value={dateTo}
            onChange={(event) => onDateToChange(event.target.value)}
            className="rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink"
          />
          <select
            value={status}
            onChange={(event) => onStatusChange(event.target.value)}
            className="rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink"
          >
            <option value="">Todos os status</option>
            <option value="scheduled">Agendada</option>
            <option value="confirmed">Confirmada</option>
            <option value="attended">Compareceu</option>
            <option value="completed">Concluida</option>
            <option value="no_show">Faltou</option>
            <option value="cancelled">Cancelada</option>
            <option value="rescheduled">Remarcada</option>
          </select>
          <select
            value={paymentStatus}
            onChange={(event) => onPaymentStatusChange(event.target.value)}
            className="rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink"
          >
            <option value="">Todos os pagamentos</option>
            <option value="pending">Pendente</option>
            <option value="paid">Pago</option>
            <option value="waived">Isento</option>
            <option value="not_required">Nao requerido</option>
            <option value="unknown">Nao informado</option>
          </select>
          <input
            type="search"
            value={searchQuery}
            onChange={(event) => onSearchQueryChange(event.target.value)}
            placeholder="Aluno, professor ou observacao..."
            className="rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink"
          />
        </div>

        {isLoading ? (
          <SkeletonList rows={6} cols={4} />
        ) : isError ? (
          <EmptyState
            icon={AlertTriangle}
            title="Nao foi possivel carregar a agenda"
            description="Tente novamente para recuperar as marcacoes importadas da planilha."
            action={{ label: "Tentar novamente", onClick: onRetry }}
          />
        ) : appointments.length === 0 ? (
          <EmptyState
            icon={CalendarDays}
            title="Nenhuma avaliacao na agenda"
            description="Importe a planilha Excel ou ajuste os filtros de periodo/status."
          />
        ) : (
          <div className="overflow-hidden rounded-2xl border border-lovable-border bg-lovable-surface">
            <div className="hidden grid-cols-[1fr_1fr_0.8fr_0.8fr_auto] gap-3 border-b border-lovable-border bg-lovable-surface-soft px-4 py-3 text-[11px] font-semibold uppercase tracking-widest text-lovable-ink-muted lg:grid">
              <span>Aluno e horario</span>
              <span>Professor</span>
              <span>Presenca</span>
              <span>Pagamento</span>
              <span className="text-right">Acoes</span>
            </div>
            <ul className="divide-y divide-lovable-border">
              {appointments.map((item) => (
                <li key={item.id} className="grid gap-3 px-4 py-4 lg:grid-cols-[1fr_1fr_0.8fr_0.8fr_auto] lg:items-center">
                  <div>
                    <p className="font-semibold text-lovable-ink">{item.member_name ?? "Aluno sem nome"}</p>
                    <p className="mt-1 text-xs text-lovable-ink-muted">{formatDateTime(item.scheduled_at)}</p>
                    <p className="mt-1 text-[11px] uppercase tracking-wider text-lovable-ink-muted">{item.assessment_type}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-lovable-ink">
                      {item.evaluator_name ?? item.evaluator_name_raw ?? "Professor nao informado"}
                    </p>
                    {item.notes ? <p className="mt-1 line-clamp-2 text-xs text-lovable-ink-muted">{item.notes}</p> : null}
                  </div>
                  <span className="rounded-full border border-lovable-border bg-lovable-surface-soft px-3 py-1 text-xs font-semibold text-lovable-ink">
                    {getAppointmentStatusLabel(item.status)}
                  </span>
                  <span className="rounded-full border border-lovable-border bg-lovable-surface-soft px-3 py-1 text-xs font-semibold text-lovable-ink">
                    {getPaymentStatusLabel(item.payment_status)}
                  </span>
                  <div className="flex flex-wrap items-center gap-2 lg:justify-end">
                    <button
                      type="button"
                      disabled={updatingAppointmentId === item.id}
                      onClick={() => onUpdateAppointment(item.id, { status: "attended" })}
                      className="rounded-lg border border-emerald-400 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-900 disabled:opacity-60"
                    >
                      Compareceu
                    </button>
                    <button
                      type="button"
                      disabled={updatingAppointmentId === item.id}
                      onClick={() => onUpdateAppointment(item.id, { status: "no_show" })}
                      className="rounded-lg border border-amber-400 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900 disabled:opacity-60"
                    >
                      Faltou
                    </button>
                    <button
                      type="button"
                      disabled={updatingAppointmentId === item.id}
                      onClick={() => onUpdateAppointment(item.id, { payment_status: "paid" })}
                      className="rounded-lg border border-lovable-border px-3 py-2 text-xs font-semibold text-lovable-ink disabled:opacity-60"
                    >
                      Pago
                    </button>
                    <Link
                      to={`/assessments/members/${item.member_id}`}
                      className="rounded-lg border border-lovable-border px-3 py-2 text-xs font-semibold text-lovable-ink hover:bg-lovable-surface-soft"
                    >
                      Perfil
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function AssessmentsPage() {
  const queryClient = useQueryClient();
  const [activeView, setActiveView] = useState<AssessmentWorkspaceView>("queue");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<AssessmentQueueFilter>("all");
  const [activeShift, setActiveShift] = useState<PreferredShiftFilter>("all");
  const [page, setPage] = useState(1);
  const [appointmentDateFrom, setAppointmentDateFrom] = useState(() => toDateInputValue(addDays(new Date(), -7)));
  const [appointmentDateTo, setAppointmentDateTo] = useState(() => toDateInputValue(addDays(new Date(), 14)));
  const [appointmentStatus, setAppointmentStatus] = useState("");
  const [appointmentPaymentStatus, setAppointmentPaymentStatus] = useState("");

  useEffect(() => {
    setPage(1);
  }, [activeFilter, activeShift, searchQuery]);

  const dashboardQuery = useQuery({
    queryKey: ["assessments", "dashboard"],
    queryFn: () => assessmentService.dashboard(),
    staleTime: 5 * 60 * 1000,
  });

  const queueQuery = useQuery({
    queryKey: ["assessments", "queue", activeFilter, activeShift, searchQuery, page],
    queryFn: () =>
      assessmentService.queue({
        page,
        page_size: 50,
        search: searchQuery,
        bucket: activeFilter,
        preferred_shift: activeShift === "all" ? undefined : activeShift,
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

  const appointmentsQuery = useQuery({
    queryKey: [
      "assessments",
      "appointments",
      appointmentDateFrom,
      appointmentDateTo,
      appointmentStatus,
      appointmentPaymentStatus,
      searchQuery,
    ],
    queryFn: () =>
      assessmentService.appointments({
        page: 1,
        page_size: 100,
        date_from: appointmentDateFrom || undefined,
        date_to: appointmentDateTo || undefined,
        status: appointmentStatus || undefined,
        payment_status: appointmentPaymentStatus || undefined,
        search: searchQuery,
      }),
    enabled: activeView === "agenda",
    staleTime: 60 * 1000,
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

  const updateAppointmentMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<AssessmentAppointment> }) =>
      assessmentService.updateAppointment(id, payload),
    onSuccess: () => {
      toast.success("Agenda atualizada.");
      void queryClient.invalidateQueries({ queryKey: ["assessments"] });
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["member-timeline"] });
    },
    onError: () => {
      toast.error("Nao foi possivel atualizar a agenda.");
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
      <div className="inline-flex rounded-2xl border border-lovable-border bg-lovable-surface p-1">
        <button
          type="button"
          onClick={() => setActiveView("queue")}
          className={`rounded-xl px-4 py-2 text-xs font-semibold uppercase tracking-wider ${
            activeView === "queue" ? "bg-lovable-primary text-white" : "text-lovable-ink-muted hover:text-lovable-ink"
          }`}
        >
          Fila de avaliacoes
        </button>
        <button
          type="button"
          onClick={() => setActiveView("agenda")}
          className={`rounded-xl px-4 py-2 text-xs font-semibold uppercase tracking-wider ${
            activeView === "agenda" ? "bg-lovable-primary text-white" : "text-lovable-ink-muted hover:text-lovable-ink"
          }`}
        >
          Agenda Excel
        </button>
      </div>

      {activeView === "agenda" ? (
        <AssessmentAgendaPanel
          appointments={appointmentsQuery.data?.items ?? []}
          isLoading={appointmentsQuery.isLoading}
          isFetching={appointmentsQuery.isFetching}
          isError={appointmentsQuery.isError}
          dateFrom={appointmentDateFrom}
          dateTo={appointmentDateTo}
          status={appointmentStatus}
          paymentStatus={appointmentPaymentStatus}
          searchQuery={searchQuery}
          onDateFromChange={setAppointmentDateFrom}
          onDateToChange={setAppointmentDateTo}
          onStatusChange={setAppointmentStatus}
          onPaymentStatusChange={setAppointmentPaymentStatus}
          onSearchQueryChange={setSearchQuery}
          onRetry={() => void appointmentsQuery.refetch()}
          updatingAppointmentId={updateAppointmentMutation.variables?.id ?? null}
          onUpdateAppointment={(id, payload) => updateAppointmentMutation.mutate({ id, payload })}
        />
      ) : (
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
          activeShift={activeShift}
          onActiveShiftChange={setActiveShift}
          page={page}
          onPageChange={setPage}
          onClearFilters={() => {
            setSearchQuery("");
            setActiveFilter("all");
            setActiveShift("all");
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
      )}

      {activeView === "queue" ? <Card>
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
      </Card> : null}
    </div>
  );
}
