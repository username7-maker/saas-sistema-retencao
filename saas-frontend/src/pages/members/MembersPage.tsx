import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, UserPlus, X, Edit2, Trash2 } from "lucide-react";
import toast from "react-hot-toast";

import { memberService } from "../../services/memberService";
import type { Member, RiskLevel } from "../../types";
import { Badge, Button, Card, CardContent, Dialog, Input, Pagination, Select } from "../../components/ui2";
import { AddMemberDrawer } from "./AddMemberDrawer";
import { EditMemberDrawer } from "./EditMemberDrawer";
import { MemberDetailDrawer } from "./MemberDetailDrawer";
import { PAGE_SIZE, RISK_LABELS, RISK_VARIANTS, STATUS_LABELS, STATUS_VARIANTS } from "./memberUtils";
import type { MemberQueryFilters } from "./memberUtils";

export function MembersPage() {
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

  const handleSearch = () => {
    setPage(1);
    setFilters((prev) => ({ ...prev, search: search.trim() || undefined }));
  };

  const handleFilterChange = (key: keyof MemberQueryFilters, value: string | undefined) => {
    setPage(1);
    setFilters((prev) => ({ ...prev, [key]: value || undefined }));
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-display text-2xl font-bold text-lovable-ink">Membros</h2>
          <p className="text-sm text-lovable-ink-muted">{data ? `${data.total} membros cadastrados` : "Carregando..."}</p>
        </div>
        <Button variant="primary" onClick={() => setAddOpen(true)}>
          + Adicionar Membro
        </Button>
      </div>

      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex min-w-[220px] flex-1 gap-2">
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    handleSearch();
                  }
                }}
                placeholder="Buscar por nome ou email..."
                className="flex-1"
              />
              <Button variant="primary" size="sm" onClick={handleSearch}>
                <Search size={14} />
              </Button>
              {filters.search ? (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSearch("");
                    setPage(1);
                    setFilters((prev) => ({ ...prev, search: undefined }));
                  }}
                >
                  <X size={14} />
                </Button>
              ) : null}
            </div>

            <div className="w-full md:w-56">
              <Select
                value={filters.status ?? ""}
                onChange={(event) => handleFilterChange("status", event.target.value as Member["status"] | undefined)}
              >
                <option value="">Todos os status</option>
                <option value="active">Ativo</option>
                <option value="paused">Pausado</option>
                <option value="cancelled">Cancelado</option>
              </Select>
            </div>

            <div className="w-full md:w-56">
              <Select
                value={filters.risk_level ?? ""}
                onChange={(event) => handleFilterChange("risk_level", event.target.value as RiskLevel | undefined)}
              >
                <option value="">Todos os riscos</option>
                <option value="green">Verde</option>
                <option value="yellow">Amarelo</option>
                <option value="red">Vermelho</option>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12 text-lovable-ink-muted">Carregando membros...</div>
          ) : isError ? (
            <div className="flex items-center justify-center py-12 text-red-500">Erro ao carregar membros. Tente novamente.</div>
          ) : !data?.items.length ? (
            <div className="flex flex-col items-center justify-center py-12 text-lovable-ink-muted">
              <UserPlus size={40} className="mb-3 opacity-40" />
              <p>Nenhum membro encontrado</p>
              {filters.search ? <p className="mt-1 text-xs">Tente buscar com outro termo</p> : null}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-lovable-border bg-lovable-surface-soft">
                    <th className="px-4 py-3 text-left font-semibold text-lovable-ink-muted">Nome</th>
                    <th className="px-4 py-3 text-left font-semibold text-lovable-ink-muted">Plano</th>
                    <th className="px-4 py-3 text-left font-semibold text-lovable-ink-muted">Status</th>
                    <th className="px-4 py-3 text-left font-semibold text-lovable-ink-muted">Risco</th>
                    <th className="px-4 py-3 text-left font-semibold text-lovable-ink-muted">Ultimo Check-in</th>
                    <th className="px-4 py-3 text-left font-semibold text-lovable-ink-muted">Acoes</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((member) => (
                    <tr
                      key={member.id}
                      className="cursor-pointer border-b border-lovable-border/50 transition hover:bg-lovable-surface-soft/40"
                      onClick={() => openDetail(member)}
                    >
                      <td className="px-4 py-3">
                        <div>
                          <p className="font-medium text-lovable-ink">{member.full_name}</p>
                          <p className="text-xs text-lovable-ink-muted">{member.email ?? "Sem email"}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div>
                          <p className="text-lovable-ink">{member.plan_name}</p>
                          <p className="text-xs text-lovable-ink-muted">
                            {member.monthly_fee.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                          </p>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={STATUS_VARIANTS[member.status]}>{STATUS_LABELS[member.status]}</Badge>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Badge variant={RISK_VARIANTS[member.risk_level]}>{RISK_LABELS[member.risk_level]}</Badge>
                          <span className="text-xs text-lovable-ink-muted">{member.risk_score} pts</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-lovable-ink-muted">
                        {member.last_checkin_at ? new Date(member.last_checkin_at).toLocaleDateString("pt-BR") : "Nunca"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1" onClick={(event) => event.stopPropagation()}>
                          <Button variant="ghost" size="sm" onClick={(event) => openEdit(member, event)} title="Editar">
                            <Edit2 size={14} />
                          </Button>
                          <Button variant="danger" size="sm" onClick={() => setMemberToDelete(member)} title="Excluir">
                            <Trash2 size={14} />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>

        {data && data.total > PAGE_SIZE ? (
          <div className="flex flex-col gap-3 border-t border-lovable-border px-4 py-3 md:flex-row md:items-center md:justify-between">
            <p className="text-sm text-lovable-ink-muted">
              Mostrando {pageStart}-{pageEnd} de {data.total}
            </p>
            <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPageChange={setPage} />
          </div>
        ) : null}
      </Card>

      <AddMemberDrawer open={addOpen} onClose={() => setAddOpen(false)} />
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
