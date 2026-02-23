import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UserPlus, ToggleLeft, ToggleRight } from "lucide-react";
import toast from "react-hot-toast";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { userService, type StaffUser } from "../../services/userService";
import { useAuth } from "../../hooks/useAuth";
import { Badge, Button, Drawer, Input } from "../../components/ui2";

// ─── Role labels ──────────────────────────────────────────────────────────────

const ROLE_LABELS: Record<StaffUser["role"], string> = {
  owner: "Proprietário",
  manager: "Gerente",
  receptionist: "Recepcionista",
  salesperson: "Vendedor",
  trainer: "Instrutor",
};

const ROLE_OPTIONS: Array<{ value: StaffUser["role"]; label: string }> = [
  { value: "manager", label: "Gerente" },
  { value: "receptionist", label: "Recepcionista" },
  { value: "salesperson", label: "Vendedor" },
  { value: "trainer", label: "Instrutor" },
];

// ─── Create user form ─────────────────────────────────────────────────────────

const createSchema = z.object({
  full_name: z.string().min(2, "Nome deve ter pelo menos 2 caracteres"),
  email: z.string().email("E-mail inválido"),
  password: z.string().min(8, "Senha deve ter pelo menos 8 caracteres"),
  role: z.enum(["manager", "receptionist", "salesperson", "trainer"]),
});

type CreateFormValues = z.infer<typeof createSchema>;

interface CreateUserDrawerProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}

function CreateUserDrawer({ open, onClose, onSaved }: CreateUserDrawerProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateFormValues>({
    resolver: zodResolver(createSchema),
    defaultValues: { role: "receptionist" },
  });

  const createMutation = useMutation({
    mutationFn: userService.createUser,
    onSuccess: () => {
      toast.success("Usuário criado com sucesso!");
      reset();
      onSaved();
      onClose();
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      const msg = err?.response?.data?.detail ?? "Erro ao criar usuário.";
      toast.error(msg);
    },
  });

  const isPending = isSubmitting || createMutation.isPending;

  return (
    <Drawer open={open} onClose={onClose} title="Novo Usuário">
      <form onSubmit={handleSubmit((v) => createMutation.mutate(v))} className="flex flex-col gap-4 p-1">
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
            Nome completo *
          </label>
          <Input {...register("full_name")} placeholder="Nome do colaborador" />
          {errors.full_name && <p className="mt-1 text-xs text-red-500">{errors.full_name.message}</p>}
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
            E-mail *
          </label>
          <Input {...register("email")} type="email" placeholder="email@academia.com" />
          {errors.email && <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>}
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
            Senha provisória *
          </label>
          <Input {...register("password")} type="password" placeholder="Mínimo 8 caracteres" />
          {errors.password && <p className="mt-1 text-xs text-red-500">{errors.password.message}</p>}
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
            Função *
          </label>
          <select
            {...register("role")}
            className="w-full rounded-xl border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary"
          >
            {ROLE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          {errors.role && <p className="mt-1 text-xs text-red-500">{errors.role.message}</p>}
        </div>

        <div className="flex gap-2 pt-2">
          <Button type="submit" variant="primary" disabled={isPending} className="flex-1">
            {isPending ? "Criando..." : "Criar Usuário"}
          </Button>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
        </div>
      </form>
    </Drawer>
  );
}

// ─── User row ─────────────────────────────────────────────────────────────────

function UserRow({ user, currentUserId }: { user: StaffUser; currentUserId: string }) {
  const queryClient = useQueryClient();

  const toggleMutation = useMutation({
    mutationFn: (is_active: boolean) => userService.updateUser(user.id, { is_active }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: () => toast.error("Não foi possível alterar o usuário."),
  });

  const isSelf = user.id === currentUserId;

  return (
    <article className="flex flex-col gap-3 rounded-2xl border border-lovable-border bg-lovable-surface p-4 md:flex-row md:items-center md:justify-between">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold text-lovable-ink">{user.full_name}</p>
          <Badge variant={user.is_active ? "success" : "neutral"}>
            {user.is_active ? "Ativo" : "Inativo"}
          </Badge>
        </div>
        <p className="text-xs text-lovable-ink-muted">{user.email}</p>
        <p className="mt-1 text-xs uppercase tracking-wide text-lovable-ink-muted">
          {ROLE_LABELS[user.role] ?? user.role}
        </p>
      </div>

      {!isSelf && (
        <button
          type="button"
          onClick={() => toggleMutation.mutate(!user.is_active)}
          disabled={toggleMutation.isPending}
          className="text-lovable-ink-muted hover:text-lovable-primary disabled:opacity-50"
          title={user.is_active ? "Desativar acesso" : "Ativar acesso"}
        >
          {user.is_active
            ? <ToggleRight size={24} className="text-lovable-primary" />
            : <ToggleLeft size={24} />}
        </button>
      )}
    </article>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function UsersPage() {
  const { user: currentUser } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const queryClient = useQueryClient();

  const usersQuery = useQuery({
    queryKey: ["users"],
    queryFn: userService.listUsers,
    staleTime: 30 * 1000,
  });

  if (usersQuery.isLoading) {
    return <LoadingPanel text="Carregando usuários..." />;
  }

  const users = usersQuery.data ?? [];

  return (
    <section className="space-y-6">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Usuários</h2>
          <p className="text-sm text-lovable-ink-muted">Gerencie a equipe da academia.</p>
        </div>
        <Button variant="primary" onClick={() => setDrawerOpen(true)}>
          <UserPlus size={14} />
          Novo Usuário
        </Button>
      </header>

      {users.length === 0 ? (
        <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-8 text-center">
          <p className="text-lovable-ink-muted">Nenhum usuário cadastrado além de você.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {users.map((u) => (
            <UserRow key={u.id} user={u} currentUserId={currentUser?.id ?? ""} />
          ))}
        </div>
      )}

      <CreateUserDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onSaved={() => void queryClient.invalidateQueries({ queryKey: ["users"] })}
      />
    </section>
  );
}
