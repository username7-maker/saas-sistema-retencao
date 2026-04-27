import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, RotateCcw, Trash2, UserPlus } from "lucide-react";
import toast from "react-hot-toast";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { UserAvatar } from "../../components/common/UserAvatar";
import { userService, type StaffUser } from "../../services/userService";
import { useAuth } from "../../hooks/useAuth";
import { Badge, Button, Dialog, Drawer, FormField, Input, Select } from "../../components/ui2";
import { canChangeUserRole, canCreateUsers, canEditTargetUserProfile, canEditTargetUserRole, canToggleTargetUser, getAssignableUserRoles } from "../../utils/roleAccess";
import { getPreferredShiftLabel } from "../../utils/preferredShift";

const ROLE_LABELS: Record<StaffUser["role"], string> = {
  owner: "Proprietário",
  manager: "Gerente",
  receptionist: "Recepcionista",
  salesperson: "Comercial",
  trainer: "Instrutor",
};

const ROLE_BADGE: Record<StaffUser["role"], string> = {
  owner: "bg-lovable-primary/15 text-lovable-primary",
  manager: "bg-lovable-warning/15 text-lovable-warning",
  receptionist: "bg-lovable-surface-soft text-lovable-ink-muted",
  salesperson: "bg-lovable-surface-soft text-lovable-ink-muted",
  trainer: "bg-lovable-surface-soft text-lovable-ink-muted",
};

const SHIFT_OPTIONS = [
  { value: "", label: "Sem turno fixo" },
  { value: "morning", label: "Manha" },
  { value: "afternoon", label: "Tarde" },
  { value: "evening", label: "Noite" },
] as const;

const createSchema = z.object({
  full_name: z.string().min(2, "Nome deve ter pelo menos 2 caracteres"),
  email: z.string().email("E-mail inválido"),
  password: z.string().min(8, "Senha deve ter pelo menos 8 caracteres"),
  role: z.enum(["manager", "receptionist", "salesperson", "trainer"]),
  job_title: z.string().max(120, "Cargo muito longo").optional().or(z.literal("")),
  work_shift: z.enum(["morning", "afternoon", "evening"]).optional().or(z.literal("")),
  avatar_url: z.string().url("Informe uma URL válida para a foto").optional().or(z.literal("")),
});

const editSchema = z.object({
  full_name: z.string().min(2, "Nome deve ter pelo menos 2 caracteres"),
  role: z.enum(["manager", "receptionist", "salesperson", "trainer"]).optional(),
  job_title: z.string().max(120, "Cargo muito longo").optional().or(z.literal("")),
  work_shift: z.enum(["morning", "afternoon", "evening"]).optional().or(z.literal("")),
  avatar_url: z.string().url("Informe uma URL válida para a foto").optional().or(z.literal("")),
});

type CreateFormValues = z.infer<typeof createSchema>;
type EditFormValues = z.infer<typeof editSchema>;

function roleOptionsFor(assignableRoles: StaffUser["role"][]) {
  return assignableRoles.map((value) => ({
    value,
    label: ROLE_LABELS[value],
  }));
}

interface CreateUserDrawerProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  assignableRoles: StaffUser["role"][];
}

function CreateUserDrawer({ open, onClose, onSaved, assignableRoles }: CreateUserDrawerProps) {
  const options = roleOptionsFor(assignableRoles);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateFormValues>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      role: (options[0]?.value ?? "receptionist") as CreateFormValues["role"],
      job_title: "",
      work_shift: "",
      avatar_url: "",
    },
  });

  const createMutation = useMutation({
    mutationFn: userService.createUser,
    onSuccess: () => {
      toast.success("Usuário criado com sucesso.");
      reset();
      onSaved();
      onClose();
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      toast.error(err?.response?.data?.detail ?? "Erro ao criar usuário.");
    },
  });

  const isPending = isSubmitting || createMutation.isPending;

  return (
    <Drawer open={open} onClose={onClose} title="Novo usuário">
      <form
        onSubmit={handleSubmit((values) =>
          createMutation.mutate({
            ...values,
            job_title: values.job_title?.trim() || null,
            work_shift: values.work_shift || null,
            avatar_url: values.avatar_url?.trim() || null,
          }),
        )}
        className="flex flex-col gap-4 p-4"
      >
        <FormField label="Nome completo" required error={errors.full_name?.message}>
          <Input {...register("full_name")} placeholder="Nome do colaborador" />
        </FormField>

        <FormField label="E-mail" required error={errors.email?.message}>
          <Input {...register("email")} type="email" placeholder="email@academia.com" />
        </FormField>

        <FormField label="Senha provisória" required error={errors.password?.message}>
          <Input {...register("password")} type="password" placeholder="Mínimo 8 caracteres" />
        </FormField>

        <FormField label="Papel de acesso" required error={errors.role?.message}>
          <Select {...register("role")}>
            {options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </FormField>

        <FormField label="Cargo exibido" error={errors.job_title?.message}>
          <Input {...register("job_title")} placeholder="Ex.: Head Coach, Recepção, Comercial" />
        </FormField>

        <FormField label="Turno operacional" error={errors.work_shift?.message}>
          <Select {...register("work_shift")}>
            {SHIFT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </FormField>

        <FormField label="URL da foto" error={errors.avatar_url?.message}>
          <Input {...register("avatar_url")} placeholder="https://..." />
        </FormField>

        <div className="flex gap-2 pt-2">
          <Button type="submit" variant="primary" disabled={isPending} className="flex-1">
            {isPending ? "Criando..." : "Criar usuário"}
          </Button>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
        </div>
      </form>
    </Drawer>
  );
}

interface EditUserDrawerProps {
  open: boolean;
  onClose: () => void;
  user: StaffUser | null;
  currentUserRole: StaffUser["role"];
  onSaved: () => void;
}

function EditUserDrawer({ open, onClose, user, currentUserRole, onSaved }: EditUserDrawerProps) {
  const canEditRole = user ? canEditTargetUserRole(currentUserRole, user.role, false) : false;
  const assignableRoles = getAssignableUserRoles(currentUserRole);
  const options = roleOptionsFor(assignableRoles);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<EditFormValues>({
    resolver: zodResolver(editSchema),
  });

  useEffect(() => {
    if (!user) return;
    reset({
      full_name: user.full_name,
      role: user.role === "owner" ? undefined : user.role,
      job_title: user.job_title ?? "",
      work_shift: user.work_shift ?? "",
      avatar_url: user.avatar_url ?? "",
    });
  }, [reset, user]);

  const editMutation = useMutation({
    mutationFn: async (values: EditFormValues) => {
      if (!user) {
        throw new Error("Usuário ausente");
      }

        const profilePayload = {
          full_name: values.full_name,
          job_title: values.job_title?.trim() || null,
          work_shift: values.work_shift || null,
          avatar_url: values.avatar_url?.trim() || null,
        };

      if (canEditRole && values.role && values.role !== user.role) {
        await userService.updateUser(user.id, {
          full_name: values.full_name,
          job_title: values.job_title?.trim() || null,
          work_shift: values.work_shift || null,
          avatar_url: values.avatar_url?.trim() || null,
          role: values.role,
        });
        return;
      }

      await userService.updateUserProfile(user.id, profilePayload);
    },
    onSuccess: () => {
      toast.success("Usuário atualizado com sucesso.");
      onSaved();
      onClose();
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      toast.error(err?.response?.data?.detail ?? "Erro ao atualizar usuário.");
    },
  });

  const isPending = isSubmitting || editMutation.isPending;

  return (
    <Drawer open={open} onClose={onClose} title="Editar usuário" side="right">
      {user ? (
        <form onSubmit={handleSubmit((values) => editMutation.mutate(values))} className="flex flex-col gap-4 p-4">
          <div className="flex items-center gap-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft/60 p-3">
            <UserAvatar fullName={user.full_name} avatarUrl={user.avatar_url} size="md" />
            <div>
              <p className="text-sm font-semibold text-lovable-ink">{user.full_name}</p>
              <p className="text-xs uppercase tracking-[0.18em] text-lovable-ink-muted">{user.job_title || ROLE_LABELS[user.role]}</p>
            </div>
          </div>

          <FormField label="Nome completo" required error={errors.full_name?.message}>
            <Input {...register("full_name")} placeholder="Nome do colaborador" />
          </FormField>

          {canEditRole ? (
            <FormField label="Papel de acesso" error={errors.role?.message}>
              <Select {...register("role")}>
                {options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </FormField>
          ) : null}

          <FormField label="Cargo exibido" error={errors.job_title?.message}>
            <Input {...register("job_title")} placeholder="Ex.: Head Coach, Recepção, Comercial" />
          </FormField>

          <FormField label="Turno operacional" error={errors.work_shift?.message}>
            <Select {...register("work_shift")}>
              {SHIFT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </FormField>

          <FormField label="URL da foto" error={errors.avatar_url?.message}>
            <Input {...register("avatar_url")} placeholder="https://..." />
          </FormField>

          <div className="flex gap-2 pt-2">
            <Button type="submit" variant="primary" disabled={isPending} className="flex-1">
              {isPending ? "Salvando..." : "Salvar alterações"}
            </Button>
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancelar
            </Button>
          </div>
        </form>
      ) : null}
    </Drawer>
  );
}

function UserRow({
  user,
  currentUserId,
  currentUserRole,
  onDeactivate,
  onActivate,
  onEdit,
  isPending,
  canChangeStatus,
}: {
  user: StaffUser;
  currentUserId: string;
  currentUserRole: StaffUser["role"];
  onDeactivate: (user: StaffUser) => void;
  onActivate: (user: StaffUser) => void;
  onEdit: (user: StaffUser) => void;
  isPending: boolean;
  canChangeStatus: boolean;
}) {
  const isSelf = user.id === currentUserId;
  const canToggle = canToggleTargetUser(currentUserRole, user.role, isSelf);
  const canEdit = canEditTargetUserProfile(currentUserRole, user.role, isSelf);

  return (
    <article className="flex flex-col gap-4 rounded-2xl border border-lovable-border bg-lovable-surface p-4 md:flex-row md:items-center md:justify-between">
      <div className="flex items-start gap-3">
        <UserAvatar fullName={user.full_name} avatarUrl={user.avatar_url} size="md" />
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-lovable-ink">{user.full_name}</p>
            <Badge variant={user.is_active ? "success" : "neutral"}>{user.is_active ? "Ativo" : "Inativo"}</Badge>
          </div>
          <p className="text-xs text-lovable-ink-muted">{user.email}</p>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${ROLE_BADGE[user.role]}`}>
              {ROLE_LABELS[user.role]}
            </span>
            {user.job_title ? <span className="text-xs text-lovable-ink-muted">{user.job_title}</span> : null}
            {user.work_shift ? <Badge variant="neutral">Turno {getPreferredShiftLabel(user.work_shift)}</Badge> : null}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {canEdit ? (
          <Button type="button" variant="secondary" size="sm" onClick={() => onEdit(user)} disabled={isPending}>
            <Pencil size={14} />
            Editar
          </Button>
        ) : null}

        {canToggle ? (
          user.is_active ? (
            <Button type="button" variant="danger" size="sm" onClick={() => onDeactivate(user)} disabled={isPending}>
              <Trash2 size={14} />
              Desativar
            </Button>
          ) : (
            <Button type="button" variant="secondary" size="sm" onClick={() => onActivate(user)} disabled={isPending}>
              <RotateCcw size={14} />
              Reativar
            </Button>
          )
        ) : null}
      </div>
    </article>
  );
}

export function UsersPage() {
  const { user: currentUser } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<StaffUser | null>(null);
  const [userToDeactivate, setUserToDeactivate] = useState<StaffUser | null>(null);
  const [roleFilter, setRoleFilter] = useState<StaffUser["role"] | "all">("all");
  const queryClient = useQueryClient();

  const usersQuery = useQuery({
    queryKey: ["users"],
    queryFn: userService.listUsers,
    staleTime: 30 * 1000,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ userId, is_active }: { userId: string; is_active: boolean }) => userService.setUserActive(userId, is_active),
    onSuccess: (_, variables) => {
      toast.success(variables.is_active ? "Usuário reativado com sucesso." : "Usuário desativado com sucesso.");
      setUserToDeactivate(null);
      void queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: () => toast.error("Não foi possível atualizar o usuário."),
  });

  if (usersQuery.isLoading) {
    return <LoadingPanel text="Carregando usuários..." />;
  }

  const allUsers = usersQuery.data ?? [];
  const users = roleFilter === "all" ? allUsers : allUsers.filter((item) => item.role === roleFilter);
  const assignableRoles = getAssignableUserRoles(currentUser?.role);
  const canCreateTeamUsers = canCreateUsers(currentUser?.role);
  const canEditRoles = canChangeUserRole(currentUser?.role);

  return (
    <section className="space-y-6">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Usuários</h2>
          <p className="text-sm text-lovable-ink-muted">Gerencie a equipe, personalize perfil exibido e atribua papéis de acesso.</p>
        </div>
        {canCreateTeamUsers ? (
          <Button variant="primary" onClick={() => setDrawerOpen(true)}>
            <UserPlus size={14} />
            Novo usuário
          </Button>
        ) : null}
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <label className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Filtrar por papel:</label>
        <select
          value={roleFilter}
          onChange={(event) => setRoleFilter(event.target.value as StaffUser["role"] | "all")}
          className="rounded-lg border border-lovable-border bg-lovable-surface px-3 py-1.5 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary"
        >
          <option value="all">Todos os papéis</option>
          <option value="owner">Proprietário</option>
          <option value="manager">Gerente</option>
          <option value="receptionist">Recepcionista</option>
          <option value="salesperson">Comercial</option>
          <option value="trainer">Instrutor</option>
        </select>
        <span className="text-xs text-lovable-ink-muted">{users.length} usuário{users.length !== 1 ? "s" : ""}</span>
        {canEditRoles ? <Badge variant="info">Owner pode alterar papéis</Badge> : null}
      </div>

      {users.length === 0 ? (
        <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-8 text-center">
          <p className="text-lovable-ink-muted">Nenhum usuário cadastrado além de você.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {users.map((staff) => (
            <UserRow
              key={staff.id}
              user={staff}
              currentUserId={currentUser?.id ?? ""}
              currentUserRole={currentUser?.role ?? "owner"}
              isPending={toggleMutation.isPending}
              canChangeStatus={canChangeStatus}
              onDeactivate={(targetUser) => setUserToDeactivate(targetUser)}
              onActivate={(targetUser) => toggleMutation.mutate({ userId: targetUser.id, is_active: true })}
              onEdit={setEditingUser}
            />
          ))}
        </div>
      )}

      <CreateUserDrawer
        open={drawerOpen && canCreateTeamUsers}
        onClose={() => setDrawerOpen(false)}
        onSaved={() => void queryClient.invalidateQueries({ queryKey: ["users"] })}
        assignableRoles={assignableRoles}
      />

      <EditUserDrawer
        open={Boolean(editingUser)}
        onClose={() => setEditingUser(null)}
        user={editingUser}
        currentUserRole={currentUser?.role ?? "owner"}
        onSaved={() => void queryClient.invalidateQueries({ queryKey: ["users"] })}
      />

      <Dialog
        open={Boolean(userToDeactivate)}
        onClose={() => setUserToDeactivate(null)}
        title="Desativar usuário"
        description={
          userToDeactivate
            ? `${userToDeactivate.full_name} perderá acesso ao sistema agora, mas poderá ser reativado depois. Deseja continuar?`
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
            {toggleMutation.isPending ? "Desativando..." : "Desativar"}
          </Button>
        </div>
      </Dialog>
    </section>
  );
}
