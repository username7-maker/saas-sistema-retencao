import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Edit2, Eye, Trash2, Users } from "lucide-react";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";

import { EmptyState, FilterBar, KPIStrip, PageHeader, SkeletonList, StatusBadge } from "../../components/ui";
import { PreferredShiftBadge } from "../../components/common/PreferredShiftBadge";
import {
  Badge,
  Button,
  Dialog,
  Pagination,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableInner,
  TableRow,
} from "../../components/ui2";
import { useAuth } from "../../hooks/useAuth";
import { memberService } from "../../services/memberService";
import type { MemberPlanCycle } from "../../services/memberService";
import type { Member, RiskLevel } from "../../types";
import { canDeleteMember, canManageMemberDirectory } from "../../utils/roleAccess";
import { AddMemberDrawer } from "./AddMemberDrawer";
import { EditMemberDrawer } from "./EditMemberDrawer";
import { MemberDetailDrawer } from "./MemberDetailDrawer";
import {
  getMemberExternalId,
  getUpcomingBirthdayLabel,
  isProvisionalMember,
  PAGE_SIZE,
  RISK_LABELS,
  RISK_VARIANTS,
  STATUS_LABELS,
  STATUS_VARIANTS,
} from "./memberUtils";
import type { MemberQueryFilters } from "./memberUtils";

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatCheckinDate(value: string | null): string {
  return value ? new Date(value).toLocaleDateString("pt-BR") : "Nunca";
}

function isCurrentMonth(value: string): boolean {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return false;

  const now = new Date();
  return parsed.getMonth() === now.getMonth() && parsed.getFullYear() === now.getFullYear();
}

export function MembersPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<MemberQueryFilters>({});
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [addOpen, setAddOpen] = useState(false);
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);
  const [editMember, setEditMember] = useState<Member | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [memberToDelete, setMemberToDelete] = useState<Member | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["members", filters, page],
    queryFn: () =>
      memberService.listMembers({
        ...filters,
        page,
        page_size: PAGE_SIZE,
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: memberService.deleteMember,
    onSuccess: () => {
      toast.success("Membro removido com sucesso!");
      void queryClient.invalidateQueries({ queryKey: ["members"] });
      setMemberToDelete(null);
    },
    onError: () => toast.error("Erro ao remover membro"),
  });

  const handleFilterChange = <K extends keyof MemberQueryFilters>(key: K, value: MemberQueryFilters[K] | undefined) => {
    setPage(1);
    setFilters((prev) => ({ ...prev, [key]: value === "" ? undefined : value }));
  };

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setPage(1);
    setFilters((prev) => ({ ...prev, search: value.trim() || undefined }));
  };

  const clearAllFilters = () => {
    setSearch("");
    setPage(1);
    setFilters({});
  };

  const handleProvisionalFilterChange = (value: string) => {
    setPage(1);
    setFilters((prev) => ({
      ...prev,
      provisional_only: value === "" ? undefined : value === "only",
    }));
  };

  const openDetail = (member: Member) => {
    setSelectedMember(member);
    setDetailOpen(true);
  };

  const openEdit = (member: Member, event: React.MouseEvent) => {
    event.stopPropagation();
    setEditMember(member);
    setEditOpen(true);
  };

  const pageStart = data && data.total > 0 ? (page - 1) * PAGE_SIZE + 1 : 0;
  const pageEnd = data ? Math.min(page * PAGE_SIZE, data.total) : 0;

  const kpiItems = useMemo(() => {
    const items = data?.items ?? [];
    const totalMembers = data?.total ?? 0;
    const activeMembers = items.filter((member) => member.status === "active").length;
    const redRiskMembers = items.filter((member) => member.risk_level === "red").length;
    const newThisMonth = items.filter((member) => isCurrentMonth(member.join_date)).length;

    return [
      { label: "Total de membros", value: totalMembers, tone: "neutral" as const },
      { label: "Ativos", value: activeMembers, tone: "success" as const },
      { label: "Risco vermelho", value: redRiskMembers, tone: "danger" as const },
      { label: "Novos no mês", value: newThisMonth, tone: "warning" as const },
    ];
  }, [data]);

  const activeFilterCount = [
    filters.search,
    filters.status,
    filters.risk_level,
    filters.plan_cycle,
    filters.preferred_shift,
    filters.min_days_without_checkin,
    filters.provisional_only,
  ].filter((value) => value !== undefined && value !== "").length;
  const canManageDirectory = canManageMemberDirectory(user?.role);
  const canRemoveMember = canDeleteMember(user?.role);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Membros"
        subtitle="Gestão e acompanhamento da base de alunos"
        actions={canManageDirectory ? <Button variant="primary" onClick={() => setAddOpen(true)}>+ Adicionar Membro</Button> : undefined}
      />

      <KPIStrip items={kpiItems} />

      <div className="space-y-2">
        <FilterBar
          search={{
            value: search,
            onChange: handleSearchChange,
            placeholder: "Buscar por nome, email ou matricula...",
          }}
          filters={[
            {
              key: "status",
              label: "Status",
              value: filters.status ?? "",
              onChange: (value) => handleFilterChange("status", value as Member["status"] | undefined),
              options: [
                { value: "", label: "Todos os status" },
                { value: "active", label: "Ativo" },
                { value: "paused", label: "Pausado" },
                { value: "cancelled", label: "Cancelado" },
              ],
            },
            {
              key: "risk_level",
              label: "Risco",
              value: filters.risk_level ?? "",
              onChange: (value) => handleFilterChange("risk_level", value as RiskLevel | undefined),
              options: [
                { value: "", label: "Todos os riscos" },
                { value: "green", label: "Verde" },
                { value: "yellow", label: "Amarelo" },
                { value: "red", label: "Vermelho" },
              ],
            },
            {
              key: "plan_cycle",
              label: "Plano",
              value: filters.plan_cycle ?? "",
              onChange: (value) => handleFilterChange("plan_cycle", value as MemberPlanCycle | undefined),
              options: [
                { value: "", label: "Todos os planos" },
                { value: "monthly", label: "Mensal" },
                { value: "semiannual", label: "Semestral" },
                { value: "annual", label: "Anual" },
              ],
            },
            {
              key: "preferred_shift",
              label: "Turno por check-in",
              value: filters.preferred_shift ?? "",
              onChange: (value) => handleFilterChange("preferred_shift", (value || undefined) as MemberQueryFilters["preferred_shift"]),
              options: [
                { value: "", label: "Todos os turnos por check-in" },
                { value: "morning", label: "Manha" },
                { value: "afternoon", label: "Tarde" },
                { value: "evening", label: "Noite" },
              ],
            },
            {
              key: "min_days_without_checkin",
              label: "Sem check-in",
              value: filters.min_days_without_checkin ? String(filters.min_days_without_checkin) : "",
              onChange: (value) =>
                handleFilterChange("min_days_without_checkin", value ? Number(value) : undefined),
              options: [
                { value: "", label: "Qualquer atividade" },
                { value: "7", label: "7+ dias" },
                { value: "14", label: "14+ dias" },
                { value: "30", label: "30+ dias" },
              ],
            },
            {
              key: "provisional_only",
              label: "Provisorios",
              value:
                filters.provisional_only === true
                  ? "only"
                  : filters.provisional_only === false
                    ? "exclude"
                    : "",
              onChange: handleProvisionalFilterChange,
              options: [
                { value: "", label: "Todos" },
                { value: "only", label: "Apenas provisorios" },
                { value: "exclude", label: "Ocultar provisorios" },
              ],
            },
          ]}
          activeCount={activeFilterCount}
          onClear={clearAllFilters}
        />
        <p className="px-1 text-sm text-lovable-ink-muted">
          {data ? `${data.total} membros cadastrados` : "Carregando membros..."}
        </p>
      </div>

      <Table>
        {isLoading ? (
          <div className="px-5 py-2">
            <SkeletonList rows={8} cols={6} />
          </div>
        ) : isError ? (
          <div className="flex items-center justify-center py-12 text-lovable-danger">
            Erro ao carregar membros. Tente novamente.
          </div>
        ) : !data?.items.length ? (
          <EmptyState
            icon={Users}
            title="Nenhum membro encontrado"
            description="Tente ajustar os filtros ou adicione um novo membro"
            action={canManageDirectory ? { label: "Adicionar Membro", onClick: () => setAddOpen(true) } : undefined}
          />
        ) : (
          <div className="overflow-x-auto">
            <TableInner>
              <TableHead>
                <tr>
                  <TableHeaderCell>Membro</TableHeaderCell>
                  <TableHeaderCell>Plano</TableHeaderCell>
                  <TableHeaderCell>Turno preferido</TableHeaderCell>
                  <TableHeaderCell>Operação</TableHeaderCell>
                  <TableHeaderCell>Último check-in</TableHeaderCell>
                  <TableHeaderCell className="w-[140px]">Ações</TableHeaderCell>
                </tr>
              </TableHead>

              <TableBody>
                {data.items.map((member) => {
                  const birthdayLabel = getUpcomingBirthdayLabel(member);
                  return (
                  <TableRow key={member.id} className="cursor-pointer" onClick={() => openDetail(member)}>
                    <TableCell>
                      <div className="min-w-0">
                        <Link
                          to={`/assessments/members/${member.id}`}
                          className="block truncate font-medium text-lovable-ink transition hover:text-lovable-brand hover:underline"
                          onClick={(event) => event.stopPropagation()}
                        >
                          {member.full_name}
                        </Link>
                        <p className="mt-1 truncate text-xs text-lovable-ink-muted">{member.email ?? "Sem email"}</p>
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          {getMemberExternalId(member) ? (
                            <Badge variant="neutral" size="sm" className="tracking-normal normal-case">
                              Matricula {getMemberExternalId(member)}
                            </Badge>
                          ) : null}
                          {isProvisionalMember(member) ? (
                            <Badge variant="warning" size="sm">
                              Provisorio
                            </Badge>
                          ) : null}
                          {birthdayLabel ? (
                            <Badge variant="warning" size="sm" className="tracking-normal normal-case">
                              {birthdayLabel}
                            </Badge>
                          ) : null}
                        </div>
                      </div>
                    </TableCell>

                    <TableCell>
                      <div>
                        <p className="font-medium text-lovable-ink">{member.plan_name}</p>
                        <p className="mt-1 text-xs text-lovable-ink-muted">{formatCurrency(member.monthly_fee)}</p>
                      </div>
                    </TableCell>

                    <TableCell>
                      <div className="flex min-w-[132px] flex-col items-start gap-1">
                        <PreferredShiftBadge preferredShift={member.preferred_shift} prefix showFallback />
                        <span className="text-[11px] leading-tight text-lovable-ink-muted">
                          por check-ins
                        </span>
                      </div>
                    </TableCell>

                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        <StatusBadge
                          status={member.status}
                          map={{
                            active: { label: STATUS_LABELS.active, variant: STATUS_VARIANTS.active },
                            paused: { label: STATUS_LABELS.paused, variant: STATUS_VARIANTS.paused },
                            cancelled: { label: STATUS_LABELS.cancelled, variant: STATUS_VARIANTS.cancelled },
                          }}
                        />
                        <StatusBadge
                          status={member.risk_level}
                          map={{
                            green: { label: RISK_LABELS.green, variant: RISK_VARIANTS.green },
                            yellow: { label: RISK_LABELS.yellow, variant: RISK_VARIANTS.yellow },
                            red: { label: RISK_LABELS.red, variant: RISK_VARIANTS.red },
                          }}
                        />
                        <Badge variant="neutral" className="px-2 py-0.5 text-[11px] normal-case tracking-normal">
                          {member.risk_score} pts
                        </Badge>
                      </div>
                    </TableCell>

                    <TableCell>
                      <span className="text-sm text-lovable-ink-muted">{formatCheckinDate(member.last_checkin_at)}</span>
                    </TableCell>

                    <TableCell>
                      <div className="flex items-center gap-1" onClick={(event) => event.stopPropagation()}>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openDetail(member)}
                          title="Ver detalhes"
                          aria-label={`Ver detalhes de ${member.full_name}`}
                          className="px-2"
                        >
                          <Eye size={14} />
                        </Button>
                        {canManageDirectory ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(event) => openEdit(member, event)}
                            title="Editar"
                            aria-label={`Editar ${member.full_name}`}
                            className="px-2"
                          >
                            <Edit2 size={14} />
                          </Button>
                        ) : null}
                        {canRemoveMember ? (
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => setMemberToDelete(member)}
                            title="Excluir"
                            aria-label={`Excluir ${member.full_name}`}
                            className="px-2"
                          >
                            <Trash2 size={14} />
                          </Button>
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                )})}
              </TableBody>
            </TableInner>
          </div>
        )}

        {data && data.total > PAGE_SIZE ? (
          <div className="flex flex-col gap-3 border-t border-lovable-border px-4 py-3 md:flex-row md:items-center md:justify-between">
            <p className="text-sm text-lovable-ink-muted">
              Mostrando {pageStart}-{pageEnd} de {data.total}
            </p>
            <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPageChange={setPage} />
          </div>
        ) : null}
      </Table>

      <AddMemberDrawer open={addOpen && canManageDirectory} onClose={() => setAddOpen(false)} />
      <MemberDetailDrawer member={selectedMember} open={detailOpen} onClose={() => setDetailOpen(false)} />
      <EditMemberDrawer member={editMember} open={editOpen} onClose={() => setEditOpen(false)} />

      <Dialog
        open={Boolean(memberToDelete)}
        onClose={() => setMemberToDelete(null)}
        title="Excluir membro"
        description={
          memberToDelete
            ? `Tem certeza que deseja excluir ${memberToDelete.full_name}? Esta acao nao pode ser desfeita.`
            : undefined
        }
      >
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setMemberToDelete(null)}>
            Cancelar
          </Button>
          <Button
            variant="danger"
            onClick={() => {
              if (memberToDelete) {
                deleteMutation.mutate(memberToDelete.id);
              }
            }}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? "Excluindo..." : "Excluir"}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
