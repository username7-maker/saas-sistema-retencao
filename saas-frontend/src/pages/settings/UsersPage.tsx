import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UserPlus, Trash2, RotateCcw } from "lucide-react";
import toast from "react-hot-toast";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { userService, type StaffUser } from "../../services/userService";
import { useAuth } from "../../hooks/useAuth";
import { Badge, Button, Dialog, Drawer, FormField, Input, Select } from "../../components/ui2";

const ROLE_LABELS: Record<StaffUser["role"], string> = {
  owner: "Proprietario",
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

const createSchema = z.object({
  full_name: z.string().min(2, "Nome deve ter pelo menos 2 caracteres"),
  email: z.string().email("E-mail invalido"),
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
      toast.success("Usuario criado com sucesso!");
      reset();
      onSaved();
      onClose();
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      const message = err?.response?.data?.detail ?? "Erro ao criar usuario.";
      toast.error(message);
    },
  });

  const isPending = isSubmitting || createMutation.isPending;

  return (
    <Drawer open={open} onClose={onClose} title="Novo Usuario">
      <form onSubmit={handleSubmit((values) => createMutation.mutate(values))} className="flex flex-col gap-4 p-1">
        <FormField label="Nome completo" required error={errors.full_name?.message}>
          <Input {...register("full_name")} placeholder="Nome do colaborador" />
        </FormField>

        <FormField label="E-mail" required error={errors.email?.message}>
          <Input {...register("email")} type="email" placeholder="email@academia.com" />
        </FormField>

        <FormField label="Senha provisoria" required error={errors.password?.message}>
          <Input {...register("password")} type="password" placeholder="Minimo 8 caracteres" />
        </FormField>

        <FormField label="Funcao" required error={errors.role?.message}>
          <Select {...register("role")}>
            {ROLE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </FormField>

        <div className="flex gap-2 pt-2">
          <Button type="submit" variant="primary" disabled={isPending} className="flex-1">
            {isPending ? "Criando..." : "Criar Usuario"}
          </Button>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
        </div>
      </form>
    </Drawer>
  );
}

function UserRow({
  user,
  currentUserId,
  onDeactivate,
  onActivate,
  isPending,
}: {
  user: StaffUser;
  currentUserId: string;
  onDeactivate: (user: StaffUser) => void;
  onActivate: (user: StaffUser) => void;
  isPending: boolean;
}) {
  const isSelf = user.id === currentUserId;

  return (
    <article className="flex flex-col gap-3 rounded-2xl border border-lovable-border bg-lovable-surface p-4 md:flex-row md:items-center md:justify-between">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold text-lovable-ink">{user.full_name}</p>
          <Badge variant={user.is_active ? "success" : "neutral"}>{user.is_active ? "Ativo" : "Inativo"}</Badge>
        </div>
        <p className="text-xs text-lovable-ink-muted">{user.email}</p>
        <p className="mt-1 text-xs uppercase tracking-wide text-lovable-ink-muted">{ROLE_LABELS[user.role] ?? user.role}</p>
      </div>

      {isSelf ? null : (
        <div className="flex items-center gap-2">
          {user.is_active ? (
            <Button
              type="button"
              variant="danger"
              size="sm"
              onClick={() => onDeactivate(user)}
              disabled={isPending}
            >
              <Trash2 size={14} />
              Excluir
            </Button>
          ) : (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => onActivate(user)}
              disabled={isPending}
            >
              <RotateCcw size={14} />
              Reativar
            </Button>
          )}
        </div>
      )}
    </article>
  );
}

export function UsersPage() {
  const { user: currentUser } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [userToDeactivate, setUserToDeactivate] = useState<StaffUser | null>(null);
  const queryClient = useQueryClient();

  const usersQuery = useQuery({
    queryKey: ["users"],
    queryFn: userService.listUsers,
    staleTime: 30 * 1000,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ userId, is_active }: { userId: string; is_active: boolean }) =>
      userService.updateUser(userId, { is_active }),
    onSuccess: (_, variables) => {
      if (variables.is_active) {
        toast.success("Usuario reativado com sucesso.");
      } else {
        toast.success("Usuario desativado com sucesso.");
      }
      setUserToDeactivate(null);
      void queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: () => toast.error("Nao foi possivel atualizar o usuario."),
  });

  if (usersQuery.isLoading) {
    return <LoadingPanel text="Carregando usuarios..." />;
  }

  const users = usersQuery.data ?? [];

  return (
    <section className="space-y-6">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Usuarios</h2>
          <p className="text-sm text-lovable-ink-muted">Gerencie a equipe da academia.</p>
        </div>
        <Button variant="primary" onClick={() => setDrawerOpen(true)}>
          <UserPlus size={14} />
          Novo Usuario
        </Button>
      </header>

      {users.length === 0 ? (
        <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-8 text-center">
          <p className="text-lovable-ink-muted">Nenhum usuario cadastrado alem de voce.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {users.map((staff) => (
            <UserRow
              key={staff.id}
              user={staff}
              currentUserId={currentUser?.id ?? ""}
              isPending={toggleMutation.isPending}
              onDeactivate={(targetUser) => setUserToDeactivate(targetUser)}
              onActivate={(targetUser) => toggleMutation.mutate({ userId: targetUser.id, is_active: true })}
            />
          ))}
        </div>
      )}

      <CreateUserDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onSaved={() => void queryClient.invalidateQueries({ queryKey: ["users"] })}
      />

      <Dialog
        open={Boolean(userToDeactivate)}
        onClose={() => setUserToDeactivate(null)}
        title="Excluir usuario"
        description={
          userToDeactivate
            ? `Tem certeza que deseja excluir ${userToDeactivate.full_name}? Esta acao nao pode ser desfeita.`
            : undefined
        }
      >
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setUserToDeactivate(null)}>
            Cancelar
          </Button>
          <Button
            variant="danger"
            onClick={() => {
              if (userToDeactivate) {
                toggleMutation.mutate({ userId: userToDeactivate.id, is_active: false });
              }
            }}
            disabled={toggleMutation.isPending}
          >
            {toggleMutation.isPending ? "Excluindo..." : "Excluir"}
          </Button>
        </div>
      </Dialog>
    </section>
  );
}
