import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Search, UserPlus, X, Edit2, Trash2, ChevronLeft, ChevronRight } from "lucide-react";
import toast from "react-hot-toast";

import { memberService, type MemberFilters, type MemberUpdatePayload } from "../../services/memberService";
import type { Member, RiskLevel } from "../../types";
import { QuickActions } from "../../components/common/QuickActions";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Drawer, Input } from "../../components/ui2";

const RISK_LABELS: Record<RiskLevel, string> = {
  green: "Verde",
  yellow: "Amarelo",
  red: "Vermelho",
};

const RISK_VARIANTS: Record<RiskLevel, "success" | "warning" | "danger"> = {
  green: "success",
  yellow: "warning",
  red: "danger",
};

const STATUS_LABELS: Record<Member["status"], string> = {
  active: "Ativo",
  paused: "Pausado",
  cancelled: "Cancelado",
};

const STATUS_VARIANTS: Record<Member["status"], "success" | "warning" | "danger"> = {
  active: "success",
  paused: "warning",
  cancelled: "danger",
};

const editSchema = z.object({
  full_name: z.string().min(2, "Nome obrigatório"),
  email: z.string().email("Email inválido").optional().or(z.literal("")),
  phone: z.string().optional(),
  plan_name: z.string().min(1, "Plano obrigatório"),
  monthly_fee: z.coerce.number().min(0).optional(),
  status: z.enum(["active", "paused", "cancelled"]),
  preferred_shift: z.string().optional(),
});

type EditFormData = z.infer<typeof editSchema>;

function EditMemberDrawer({
  member,
  open,
  onClose,
}: {
  member: Member | null;
  open: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<EditFormData>({
    resolver: zodResolver(editSchema),
    values: member
      ? {
          full_name: member.full_name,
          email: member.email ?? "",
          phone: member.phone ?? "",
          plan_name: member.plan_name,
          monthly_fee: member.monthly_fee,
          status: member.status,
          preferred_shift: member.preferred_shift ?? "",
        }
      : undefined,
  });

  const updateMutation = useMutation({
    mutationFn: (data: MemberUpdatePayload) => memberService.updateMember(member!.id, data),
    onSuccess: () => {
      toast.success("Membro atualizado com sucesso!");
      queryClient.invalidateQueries({ queryKey: ["members"] });
      onClose();
    },
    onError: () => toast.error("Erro ao atualizar membro"),
  });

  const onSubmit = (data: EditFormData) => {
    const payload: MemberUpdatePayload = {
      ...data,
      email: data.email || undefined,
      phone: data.phone || undefined,
      preferred_shift: data.preferred_shift || undefined,
    };
    updateMutation.mutate(payload);
  };

  return (
    <Drawer open={open} onClose={() => { reset(); onClose(); }} title="Editar Membro">
      {member && (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 p-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-lovable-ink">Nome completo *</label>
            <Input {...register("full_name")} placeholder="Nome do membro" />
            {errors.full_name && <p className="mt-1 text-xs text-red-500">{errors.full_name.message}</p>}
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-lovable-ink">Email</label>
            <Input {...register("email")} type="email" placeholder="email@academia.com" />
            {errors.email && <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>}
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-lovable-ink">Telefone</label>
            <Input {...register("phone")} placeholder="(11) 99999-9999" />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-lovable-ink">Plano *</label>
            <Input {...register("plan_name")} placeholder="Ex: Mensal, Trimestral" />
            {errors.plan_name && <p className="mt-1 text-xs text-red-500">{errors.plan_name.message}</p>}
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-lovable-ink">Mensalidade (R$)</label>
            <Input {...register("monthly_fee")} type="number" step="0.01" placeholder="0.00" />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-lovable-ink">Status</label>
            <select
              {...register("status")}
              className="w-full rounded-xl border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary"
            >
              <option value="active">Ativo</option>
              <option value="paused">Pausado</option>
              <option value="cancelled">Cancelado</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-lovable-ink">Turno preferido</label>
            <select
              {...register("preferred_shift")}
              className="w-full rounded-xl border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary"
            >
              <option value="">Não definido</option>
              <option value="morning">Manhã</option>
              <option value="afternoon">Tarde</option>
              <option value="evening">Noite</option>
            </select>
          </div>

          <div className="flex gap-2 pt-2">
            <Button type="submit" variant="primary" disabled={isSubmitting} className="flex-1">
              {isSubmitting ? "Salvando..." : "Salvar"}
            </Button>
            <Button type="button" variant="ghost" onClick={() => { reset(); onClose(); }}>
              Cancelar
            </Button>
          </div>
        </form>
      )}
    </Drawer>
  );
}

function MemberDetailDrawer({
  member,
  open,
  onClose,
}: {
  member: Member | null;
  open: boolean;
  onClose: () => void;
}) {
  if (!member) return null;
  const lastCheckin = member.last_checkin_at
    ? new Date(member.last_checkin_at).toLocaleDateString("pt-BR")
    : "Nunca";

  return (
    <Drawer open={open} onClose={onClose} title={member.full_name}>
      <div className="space-y-4 p-4">
        <div className="flex items-center gap-3">
          <Badge variant={RISK_VARIANTS[member.risk_level]}>
            Risco {RISK_LABELS[member.risk_level]} ({member.risk_score})
          </Badge>
          <Badge variant={STATUS_VARIANTS[member.status]}>{STATUS_LABELS[member.status]}</Badge>
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-lovable-ink-muted">Email</p>
            <p className="font-medium text-lovable-ink">{member.email ?? "—"}</p>
          </div>
          <div>
            <p className="text-lovable-ink-muted">Telefone</p>
            <p className="font-medium text-lovable-ink">{member.phone ?? "—"}</p>
          </div>
          <div>
            <p className="text-lovable-ink-muted">Plano</p>
            <p className="font-medium text-lovable-ink">{member.plan_name}</p>
          </div>
          <div>
            <p className="text-lovable-ink-muted">Mensalidade</p>
            <p className="font-medium text-lovable-ink">
              {member.monthly_fee.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
            </p>
          </div>
          <div>
            <p className="text-lovable-ink-muted">Membro desde</p>
            <p className="font-medium text-lovable-ink">
              {new Date(member.join_date).toLocaleDateString("pt-BR")}
            </p>
          </div>
          <div>
            <p className="text-lovable-ink-muted">Último check-in</p>
            <p className="font-medium text-lovable-ink">{lastCheckin}</p>
          </div>
          <div>
            <p className="text-lovable-ink-muted">Fidelidade</p>
            <p className="font-medium text-lovable-ink">{member.loyalty_months} meses</p>
          </div>
          <div>
            <p className="text-lovable-ink-muted">NPS</p>
            <p className="font-medium text-lovable-ink">
              {member.nps_last_score > 0 ? member.nps_last_score : "—"}
            </p>
          </div>
        </div>

        <div className="border-t border-lovable-border pt-3">
          <p className="mb-2 text-sm font-semibold text-lovable-ink">Ações Rápidas</p>
          <QuickActions member={member} />
        </div>
      </div>
    </Drawer>
  );
}

export function MembersPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<MemberFilters>({ page: 1, page_size: 20 });
  const [search, setSearch] = useState("");
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);
  const [editMember, setEditMember] = useState<Member | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["members", filters],
    queryFn: () => memberService.listMembers(filters),
  });

  const deleteMutation = useMutation({
    mutationFn: memberService.deleteMember,
    onSuccess: () => {
      toast.success("Membro removido com sucesso!");
      queryClient.invalidateQueries({ queryKey: ["members"] });
    },
    onError: () => toast.error("Erro ao remover membro"),
  });

  const handleSearch = () => {
    setFilters((prev) => ({ ...prev, page: 1, search: search.trim() || undefined }));
  };

  const handleFilterChange = (key: keyof MemberFilters, value: string | undefined) => {
    setFilters((prev) => ({ ...prev, page: 1, [key]: value || undefined }));
  };

  const handleDelete = (member: Member) => {
    if (window.confirm(`Remover ${member.full_name}? Esta ação é irreversível.`)) {
      deleteMutation.mutate(member.id);
    }
  };

  const openDetail = (member: Member) => {
    setSelectedMember(member);
    setDetailOpen(true);
  };

  const openEdit = (member: Member, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditMember(member);
    setEditOpen(true);
  };

  const totalPages = data ? Math.ceil(data.total / (filters.page_size ?? 20)) : 1;
  const currentPage = filters.page ?? 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-display text-2xl font-bold text-lovable-ink">Membros</h2>
          <p className="text-sm text-lovable-ink-muted">
            {data ? `${data.total} membros cadastrados` : "Carregando..."}
          </p>
        </div>
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex flex-1 gap-2 min-w-[200px]">
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="Buscar por nome ou email..."
                className="flex-1"
              />
              <Button variant="primary" size="sm" onClick={handleSearch}>
                <Search size={14} />
              </Button>
              {(filters.search) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSearch("");
                    setFilters((prev) => ({ ...prev, page: 1, search: undefined }));
                  }}
                >
                  <X size={14} />
                </Button>
              )}
            </div>

            <select
              className="rounded-xl border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary"
              value={filters.status ?? ""}
              onChange={(e) => handleFilterChange("status", e.target.value as Member["status"] | undefined)}
            >
              <option value="">Todos os status</option>
              <option value="active">Ativo</option>
              <option value="paused">Pausado</option>
              <option value="cancelled">Cancelado</option>
            </select>

            <select
              className="rounded-xl border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary"
              value={filters.risk_level ?? ""}
              onChange={(e) => handleFilterChange("risk_level", e.target.value as RiskLevel | undefined)}
            >
              <option value="">Todos os riscos</option>
              <option value="green">Verde</option>
              <option value="yellow">Amarelo</option>
              <option value="red">Vermelho</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Tabela */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12 text-lovable-ink-muted">
              Carregando membros...
            </div>
          ) : !data?.items.length ? (
            <div className="flex flex-col items-center justify-center py-12 text-lovable-ink-muted">
              <UserPlus size={40} className="mb-3 opacity-40" />
              <p>Nenhum membro encontrado</p>
              {filters.search && (
                <p className="text-xs mt-1">Tente buscar com outro termo</p>
              )}
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
                    <th className="px-4 py-3 text-left font-semibold text-lovable-ink-muted">Último Check-in</th>
                    <th className="px-4 py-3 text-left font-semibold text-lovable-ink-muted">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((member) => (
                    <tr
                      key={member.id}
                      className="border-b border-lovable-border/50 hover:bg-lovable-surface-soft/40 cursor-pointer transition"
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
                        <Badge variant={STATUS_VARIANTS[member.status]}>
                          {STATUS_LABELS[member.status]}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Badge variant={RISK_VARIANTS[member.risk_level]}>
                            {RISK_LABELS[member.risk_level]}
                          </Badge>
                          <span className="text-xs text-lovable-ink-muted">{member.risk_score}pts</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-lovable-ink-muted">
                        {member.last_checkin_at
                          ? new Date(member.last_checkin_at).toLocaleDateString("pt-BR")
                          : "Nunca"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => openEdit(member, e)}
                            title="Editar"
                          >
                            <Edit2 size={14} />
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={(e) => { e.stopPropagation(); handleDelete(member); }}
                            title="Remover"
                          >
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

        {/* Paginação */}
        {data && data.total > (filters.page_size ?? 20) && (
          <div className="flex items-center justify-between border-t border-lovable-border px-4 py-3">
            <p className="text-sm text-lovable-ink-muted">
              Mostrando {((currentPage - 1) * (filters.page_size ?? 20)) + 1}–
              {Math.min(currentPage * (filters.page_size ?? 20), data.total)} de {data.total}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                disabled={currentPage <= 1}
                onClick={() => setFilters((prev) => ({ ...prev, page: (prev.page ?? 1) - 1 }))}
              >
                <ChevronLeft size={16} />
              </Button>
              <span className="text-sm text-lovable-ink">
                {currentPage} / {totalPages}
              </span>
              <Button
                variant="ghost"
                size="sm"
                disabled={currentPage >= totalPages}
                onClick={() => setFilters((prev) => ({ ...prev, page: (prev.page ?? 1) + 1 }))}
              >
                <ChevronRight size={16} />
              </Button>
            </div>
          </div>
        )}
      </Card>

      <MemberDetailDrawer
        member={selectedMember}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
      />

      <EditMemberDrawer
        member={editMember}
        open={editOpen}
        onClose={() => setEditOpen(false)}
      />
    </div>
  );
}
