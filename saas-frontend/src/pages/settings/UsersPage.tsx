import { useEffect, useState, type ChangeEvent } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Copy, KeyRound, Pencil, RotateCcw, Trash2, UserPlus } from "lucide-react";
import toast from "react-hot-toast";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { UserAvatar } from "../../components/common/UserAvatar";
import { userService, type StaffUser, type StaffUserCreateResponse, type StaffWorkShift } from "../../services/userService";
import { useAuth } from "../../hooks/useAuth";
import { Badge, Button, Dialog, Drawer, FormField, Input, Select, cn } from "../../components/ui2";
import { canChangeUserRole, canCreateUsers, canEditTargetUserProfile, canEditTargetUserRole, canToggleTargetUser, getAssignableUserRoles } from "../../utils/roleAccess";
import { formatPreferredShiftScope, getPreferredShiftLabel } from "../../utils/preferredShift";

const ROLE_LABELS: Record<StaffUser["role"], string> = {
  owner: "Proprietario",
  manager: "Gerente",
  receptionist: "Recepcao",
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
  { value: "overnight", label: "Madrugada" },
  { value: "morning", label: "Manha" },
  { value: "afternoon", label: "Tarde" },
  { value: "evening", label: "Noite" },
] as const;

const SHIFT_SCOPE_OPTIONS = SHIFT_OPTIONS.filter((option) => option.value) as { value: StaffWorkShift; label: string }[];
const workShiftSchema = z.enum(["overnight", "morning", "afternoon", "evening"]);
const MAX_AVATAR_UPLOAD_BYTES = 1_500_000;
const AVATAR_UPLOAD_TYPES = ["image/jpeg", "image/png", "image/webp"];

const createSchema = z
  .object({
    full_name: z.string().min(2, "Nome deve ter pelo menos 2 caracteres"),
    email: z.string().email("E-mail invalido"),
    role: z.enum(["manager", "receptionist", "salesperson", "trainer"]),
    password_setup: z.enum(["manual", "invite", "temporary"]),
    password: z.string().optional().or(z.literal("")),
    confirm_password: z.string().optional().or(z.literal("")),
    job_title: z.string().max(120, "Cargo muito longo").optional().or(z.literal("")),
    work_shift: workShiftSchema.optional().or(z.literal("")),
    work_shift_scope: z.array(workShiftSchema).optional(),
  })
  .superRefine((values, ctx) => {
    if (values.password_setup !== "manual") return;
    if (!values.password || values.password.length < 8) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["password"],
        message: "Senha deve ter pelo menos 8 caracteres",
      });
    }
    if (values.password !== values.confirm_password) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["confirm_password"],
        message: "As senhas nao coincidem",
      });
    }
  });

const editSchema = z.object({
  full_name: z.string().min(2, "Nome deve ter pelo menos 2 caracteres"),
  role: z.enum(["manager", "receptionist", "salesperson", "trainer"]).optional(),
  job_title: z.string().max(120, "Cargo muito longo").optional().or(z.literal("")),
  work_shift: workShiftSchema.optional().or(z.literal("")),
  work_shift_scope: z.array(workShiftSchema).optional(),
});

type CreateFormValues = z.infer<typeof createSchema>;
type EditFormValues = z.infer<typeof editSchema>;

interface TemporaryPasswordNotice {
  title: string;
  email: string;
  password: string;
}

function roleOptionsFor(assignableRoles: StaffUser["role"][]) {
  return assignableRoles.map((value) => ({
    value,
    label: ROLE_LABELS[value],
  }));
}

function resolveWorkShiftScope(primary: string | null | undefined, scope: StaffWorkShift[] | undefined): StaffWorkShift[] {
  const resolved: StaffWorkShift[] = [];
  const append = (value: string | null | undefined) => {
    if (value === "overnight" || value === "morning" || value === "afternoon" || value === "evening") {
      if (!resolved.includes(value)) resolved.push(value);
    }
  };
  append(primary);
  for (const value of scope ?? []) append(value);
  return resolved;
}

function validateAvatarFile(file: File): string | null {
  if (!AVATAR_UPLOAD_TYPES.includes(file.type)) {
    return "Envie uma imagem JPG, PNG ou WebP.";
  }
  if (file.size > MAX_AVATAR_UPLOAD_BYTES) {
    return "A foto precisa ter no maximo 1,5 MB.";
  }
  return null;
}

function canResetTargetPassword(actorRole: StaffUser["role"] | null | undefined, targetRole: StaffUser["role"], isSelf: boolean): boolean {
  if (isSelf) return false;
  if (actorRole === "owner") return targetRole !== "owner";
  if (actorRole === "manager") return targetRole === "receptionist" || targetRole === "salesperson" || targetRole === "trainer";
  return false;
}

function PasswordNoticeDialog({ notice, onClose }: { notice: TemporaryPasswordNotice | null; onClose: () => void }) {
  async function copyPassword() {
    if (!notice) return;
    try {
      await navigator.clipboard?.writeText(notice.password);
      toast.success("Senha copiada.");
    } catch {
      toast.error("Nao foi possivel copiar automaticamente.");
    }
  }

  return (
    <Dialog
      open={Boolean(notice)}
      onClose={onClose}
      title={notice?.title ?? "Senha provisoria"}
      description={notice ? `Envie esta senha para ${notice.email}. Ela sera exibida apenas agora.` : undefined}
    >
      {notice ? (
        <div className="space-y-4">
          <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted p-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">Senha provisoria</p>
            <code className="mt-2 block break-all rounded-xl bg-lovable-surface px-3 py-2 font-mono text-sm text-lovable-ink">
              {notice.password}
            </code>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={copyPassword}>
              <Copy size={14} />
              Copiar senha
            </Button>
            <Button type="button" variant="ghost" onClick={onClose}>
              Fechar
            </Button>
          </div>
        </div>
      ) : null}
    </Dialog>
  );
}
interface CreateUserDrawerProps {
  open: boolean;
  onClose: () => void;
  onSaved: (createdUser: StaffUserCreateResponse) => void;
  assignableRoles: StaffUser["role"][];
}

function CreateUserDrawer({ open, onClose, onSaved, assignableRoles }: CreateUserDrawerProps) {
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const options = roleOptionsFor(assignableRoles);
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<CreateFormValues>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      role: (options[0]?.value ?? "receptionist") as CreateFormValues["role"],
      password_setup: "manual",
      password: "",
      confirm_password: "",
      job_title: "",
      work_shift: "",
      work_shift_scope: [],
    },
  });
  const passwordSetup = watch("password_setup");

  const createMutation = useMutation({
    mutationFn: userService.createUser,
    onSuccess: (createdUser) => {
      if (createdUser.setup_status === "temporary_password_generated") {
        toast.success("Usuario criado com senha provisoria.");
      } else if (createdUser.setup_status === "invite_sent") {
        toast.success("Usuario criado. O convite para definir senha foi enviado.");
      } else {
        toast.success("Usuario criado com senha inicial definida.");
      }
      reset();
      setAdvancedOpen(false);
      onSaved(createdUser);
      onClose();
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      toast.error(err?.response?.data?.detail ?? "Erro ao criar usuario.");
    },
  });

  const isPending = isSubmitting || createMutation.isPending;

  return (
    <Drawer open={open} onClose={onClose} title="Novo usuario">
      <form
        onSubmit={handleSubmit((values) =>
          createMutation.mutate({
            full_name: values.full_name,
            email: values.email,
            role: values.role,
            password_setup: values.password_setup,
            password: values.password_setup === "manual" ? values.password : null,
            job_title: values.job_title?.trim() || null,
            work_shift: values.work_shift || null,
            work_shift_scope: resolveWorkShiftScope(values.work_shift || null, values.work_shift_scope),
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

        <FormField label="Papel de acesso" required error={errors.role?.message}>
          <Select {...register("role")}>
            {options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </FormField>

        <FormField label="Senha" required error={errors.password_setup?.message}>
          <Select {...register("password_setup")}>
            <option value="manual">Digitar senha agora</option>
            <option value="invite">Usuario cria a senha por convite</option>
            <option value="temporary">Gerar senha provisoria agora</option>
          </Select>
        </FormField>

        {passwordSetup === "manual" ? (
          <div className="grid gap-4 md:grid-cols-2">
            <FormField label="Senha inicial" required error={errors.password?.message}>
              <Input {...register("password")} type="password" placeholder="Minimo de 8 caracteres" autoComplete="new-password" />
            </FormField>

            <FormField label="Confirmar senha" required error={errors.confirm_password?.message}>
              <Input {...register("confirm_password")} type="password" placeholder="Repita a senha" autoComplete="new-password" />
            </FormField>
          </div>
        ) : null}

        <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/60 px-3 py-2 text-xs text-lovable-ink-muted">
          Digite a senha inicial quando for criar o acesso imediatamente. Use convite por e-mail quando o provedor estiver funcionando, ou gere senha provisoria quando solicitado.
        </div>

        <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft/45">
          <button
            type="button"
            className="flex w-full items-center justify-between px-3 py-2 text-sm font-semibold text-lovable-ink"
            onClick={() => setAdvancedOpen((current) => !current)}
            aria-expanded={advancedOpen}
          >
            Opcoes avancadas
            <ChevronDown size={15} className={cn("transition", advancedOpen ? "rotate-180" : "")} />
          </button>

          {advancedOpen ? (
            <div className="space-y-4 border-t border-lovable-border p-3">
              <FormField label="Cargo exibido" error={errors.job_title?.message}>
                <Input {...register("job_title")} placeholder="Ex.: Head Coach, Recepcao, Comercial" />
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

              <FormField label="Turnos cobertos na fila">
                <div className="grid grid-cols-2 gap-2 rounded-2xl border border-lovable-border bg-lovable-surface-soft/50 p-3">
                  {SHIFT_SCOPE_OPTIONS.map((option) => (
                    <label key={option.value} className="flex items-center gap-2 text-xs font-semibold text-lovable-ink">
                      <input type="checkbox" value={option.value} {...register("work_shift_scope")} className="accent-lovable-primary" />
                      {option.label}
                    </label>
                  ))}
                </div>
              </FormField>

              <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/60 p-3 text-xs text-lovable-ink-muted">
                A foto da equipe e enviada depois, ao editar o usuario. Assim o acesso pode ser criado rapidamente sem depender de URL manual.
              </div>
            </div>
          ) : null}
        </div>

        <div className="flex gap-2 pt-2">
          <Button type="submit" variant="primary" disabled={isPending} className="flex-1">
            {isPending ? "Criando..." : "Criar usuario"}
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
  const [avatarPreview, setAvatarPreview] = useState<string | null>(user?.avatar_url ?? null);

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
      work_shift_scope: user.work_shift_scope ?? [],
    });
    setAvatarPreview(user.avatar_url ?? null);
  }, [reset, user]);

  const editMutation = useMutation({
    mutationFn: async (values: EditFormValues) => {
      if (!user) throw new Error("Usuario ausente");

      const profilePayload = {
        full_name: values.full_name,
        job_title: values.job_title?.trim() || null,
        work_shift: values.work_shift || null,
        work_shift_scope: resolveWorkShiftScope(values.work_shift || null, values.work_shift_scope),
      };

      if (canEditRole && values.role && values.role !== user.role) {
        await userService.updateUser(user.id, { ...profilePayload, role: values.role });
        return;
      }

      await userService.updateUserProfile(user.id, profilePayload);
    },
    onSuccess: () => {
      toast.success("Usuario atualizado com sucesso.");
      onSaved();
      onClose();
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      toast.error(err?.response?.data?.detail ?? "Erro ao atualizar usuario.");
    },
  });

  const avatarUploadMutation = useMutation({
    mutationFn: (file: File) => {
      if (!user) throw new Error("Usuario ausente");
      return userService.uploadUserAvatar(user.id, file);
    },
    onSuccess: (updatedUser) => {
      setAvatarPreview(updatedUser.avatar_url ?? null);
      toast.success("Foto do usuario enviada com sucesso.");
      onSaved();
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      toast.error(err?.response?.data?.detail ?? "Nao foi possivel enviar a foto do usuario.");
    },
  });

  function handleAvatarFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    const error = validateAvatarFile(file);
    if (error) {
      toast.error(error);
      return;
    }

    avatarUploadMutation.mutate(file);
  }

  const isPending = isSubmitting || editMutation.isPending;

  return (
    <Drawer open={open} onClose={onClose} title="Editar usuario" side="right">
      {user ? (
        <form onSubmit={handleSubmit((values) => editMutation.mutate(values))} className="flex flex-col gap-4 p-4">
          <div className="flex items-center gap-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft/60 p-3">
            <UserAvatar fullName={user.full_name} avatarUrl={avatarPreview} size="md" />
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
            <Input {...register("job_title")} placeholder="Ex.: Head Coach, Recepcao, Comercial" />
          </FormField>

          <FormField label="Foto da equipe">
            <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-dashed border-lovable-border bg-lovable-surface-soft p-4">
              <input
                id={`team-avatar-upload-${user.id}`}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="sr-only"
                onChange={handleAvatarFileChange}
                disabled={avatarUploadMutation.isPending}
              />
              <label
                htmlFor={`team-avatar-upload-${user.id}`}
                className="inline-flex h-10 cursor-pointer items-center justify-center rounded-xl border border-lovable-border bg-lovable-surface px-4 text-sm font-semibold text-lovable-ink transition hover:border-lovable-border-strong hover:bg-lovable-surface-soft"
              >
                {avatarUploadMutation.isPending ? "Enviando..." : "Escolher imagem"}
              </label>
              <p className="text-xs text-lovable-ink-muted">JPG, PNG ou WebP ate 1,5 MB. Cargo e foto mudam a identidade exibida; papel muda permissao.</p>
            </div>
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

          <FormField label="Turnos cobertos na fila">
            <div className="grid grid-cols-2 gap-2 rounded-2xl border border-lovable-border bg-lovable-surface-soft/50 p-3">
              {SHIFT_SCOPE_OPTIONS.map((option) => (
                <label key={option.value} className="flex items-center gap-2 text-xs font-semibold text-lovable-ink">
                  <input type="checkbox" value={option.value} {...register("work_shift_scope")} className="accent-lovable-primary" />
                  {option.label}
                </label>
              ))}
            </div>
          </FormField>

          <div className="flex gap-2 pt-2">
            <Button type="submit" variant="primary" disabled={isPending} className="flex-1">
              {isPending ? "Salvando..." : "Salvar alteracoes"}
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
  onResetPassword,
  isPending,
  canChangeStatus,
}: {
  user: StaffUser;
  currentUserId: string;
  currentUserRole: StaffUser["role"];
  onDeactivate: (user: StaffUser) => void;
  onActivate: (user: StaffUser) => void;
  onEdit: (user: StaffUser) => void;
  onResetPassword: (user: StaffUser) => void;
  isPending: boolean;
  canChangeStatus: boolean;
}) {
  const isSelf = user.id === currentUserId;
  const canToggle = canChangeStatus && canToggleTargetUser(currentUserRole, user.role, isSelf);
  const canEdit = canEditTargetUserProfile(currentUserRole, user.role, isSelf);
  const canResetPassword = canResetTargetPassword(currentUserRole, user.role, isSelf);

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
            {formatPreferredShiftScope(user.work_shift, user.work_shift_scope) ? (
              <Badge variant="info">Fila {formatPreferredShiftScope(user.work_shift, user.work_shift_scope)}</Badge>
            ) : null}
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

        {canResetPassword ? (
          <Button type="button" variant="secondary" size="sm" onClick={() => onResetPassword(user)} disabled={isPending}>
            <KeyRound size={14} />
            Resetar senha
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
  const [userToResetPassword, setUserToResetPassword] = useState<StaffUser | null>(null);
  const [temporaryPasswordNotice, setTemporaryPasswordNotice] = useState<TemporaryPasswordNotice | null>(null);
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
      toast.success(variables.is_active ? "Usuario reativado com sucesso." : "Usuario desativado com sucesso.");
      setUserToDeactivate(null);
      void queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: () => toast.error("Nao foi possivel atualizar o usuario."),
  });

  const resetPasswordMutation = useMutation({
    mutationFn: async (targetUser: StaffUser) => ({
      targetUser,
      result: await userService.resetUserPassword(targetUser.id),
    }),
    onSuccess: ({ targetUser, result }) => {
      setUserToResetPassword(null);
      setTemporaryPasswordNotice({
        title: "Senha redefinida",
        email: targetUser.email,
        password: result.temporary_password,
      });
      toast.success("Senha provisoria gerada.");
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      toast.error(err?.response?.data?.detail ?? "Nao foi possivel resetar a senha.");
    },
  });

  if (usersQuery.isLoading) {
    return <LoadingPanel text="Carregando usuarios..." />;
  }

  const allUsers = usersQuery.data ?? [];
  const users = roleFilter === "all" ? allUsers : allUsers.filter((item) => item.role === roleFilter);
  const hasFilteredOutUsers = roleFilter !== "all" && users.length === 0 && allUsers.length > 0;
  const filteredRoleLabel = roleFilter === "all" ? "" : ROLE_LABELS[roleFilter];
  const assignableRoles = getAssignableUserRoles(currentUser?.role);
  const canCreateTeamUsers = canCreateUsers(currentUser?.role);
  const canEditRoles = canChangeUserRole(currentUser?.role);
  const canChangeStatus = canCreateTeamUsers;
  const isPending = toggleMutation.isPending || resetPasswordMutation.isPending;

  return (
    <section className="space-y-6">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Usuarios</h2>
          <p className="text-sm text-lovable-ink-muted">Crie acessos, defina senha inicial, ajuste papeis e gerencie reset de senha.</p>
        </div>
        {canCreateTeamUsers ? (
          <Button variant="primary" onClick={() => setDrawerOpen(true)}>
            <UserPlus size={14} />
            Novo usuario
          </Button>
        ) : null}
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <label className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Filtrar por papel:</label>
        <select
          aria-label="Filtrar por papel"
          value={roleFilter}
          onChange={(event) => setRoleFilter(event.target.value as StaffUser["role"] | "all")}
          className="rounded-lg border border-lovable-border bg-lovable-surface px-3 py-1.5 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary"
        >
          <option value="all">Todos os papeis</option>
          <option value="owner">Proprietario</option>
          <option value="manager">Gerente</option>
          <option value="receptionist">Recepcao</option>
          <option value="salesperson">Comercial</option>
          <option value="trainer">Instrutor</option>
        </select>
        <span className="text-xs text-lovable-ink-muted">{users.length} usuario{users.length !== 1 ? "s" : ""}</span>
        {canEditRoles ? <Badge variant="info">Owner altera papeis</Badge> : null}
      </div>

      {users.length === 0 ? (
        <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-8 text-center">
          <p className="text-lovable-ink-muted">
            {hasFilteredOutUsers
              ? `Nenhum usuario com papel ${filteredRoleLabel} neste filtro.`
              : "Nenhum usuario cadastrado alem de voce."}
          </p>
          {hasFilteredOutUsers ? (
            <Button type="button" variant="secondary" size="sm" className="mt-4" onClick={() => setRoleFilter("all")}>
              Ver todos os papeis
            </Button>
          ) : null}
        </div>
      ) : (
        <div className="space-y-3">
          {users.map((staff) => (
            <UserRow
              key={staff.id}
              user={staff}
              currentUserId={currentUser?.id ?? ""}
              currentUserRole={currentUser?.role ?? "owner"}
              isPending={isPending}
              canChangeStatus={canChangeStatus}
              onDeactivate={(targetUser) => setUserToDeactivate(targetUser)}
              onActivate={(targetUser) => toggleMutation.mutate({ userId: targetUser.id, is_active: true })}
              onEdit={setEditingUser}
              onResetPassword={setUserToResetPassword}
            />
          ))}
        </div>
      )}

      <CreateUserDrawer
        open={drawerOpen && canCreateTeamUsers}
        onClose={() => setDrawerOpen(false)}
        onSaved={(createdUser) => {
          queryClient.setQueryData<StaffUser[]>(["users"], (current) => {
            const existing = current ?? [];
            if (existing.some((item) => item.id === createdUser.id)) {
              return existing.map((item) => (item.id === createdUser.id ? createdUser : item));
            }
            return [...existing, createdUser];
          });
          setRoleFilter(createdUser.role);
          if (createdUser.temporary_password) {
            setTemporaryPasswordNotice({
              title: "Usuario criado",
              email: createdUser.email,
              password: createdUser.temporary_password,
            });
          }
          void queryClient.invalidateQueries({ queryKey: ["users"] });
        }}
        assignableRoles={assignableRoles}
      />

      <EditUserDrawer
        open={Boolean(editingUser)}
        onClose={() => setEditingUser(null)}
        user={editingUser}
        currentUserRole={currentUser?.role ?? "owner"}
        onSaved={() => void queryClient.invalidateQueries({ queryKey: ["users"] })}
      />

      <PasswordNoticeDialog notice={temporaryPasswordNotice} onClose={() => setTemporaryPasswordNotice(null)} />

      <Dialog
        open={Boolean(userToResetPassword)}
        onClose={() => setUserToResetPassword(null)}
        title="Resetar senha"
        description={
          userToResetPassword
            ? `Uma nova senha provisoria sera gerada para ${userToResetPassword.full_name} e exibida apenas uma vez.`
            : undefined
        }
      >
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setUserToResetPassword(null)}>
            Cancelar
          </Button>
          <Button
            variant="primary"
            onClick={() => {
              if (userToResetPassword) resetPasswordMutation.mutate(userToResetPassword);
            }}
            disabled={resetPasswordMutation.isPending}
          >
            {resetPasswordMutation.isPending ? "Gerando..." : "Gerar senha provisoria"}
          </Button>
        </div>
      </Dialog>

      <Dialog
        open={Boolean(userToDeactivate)}
        onClose={() => setUserToDeactivate(null)}
        title="Desativar usuario"
        description={
          userToDeactivate
            ? `${userToDeactivate.full_name} perdera acesso ao sistema agora, mas podera ser reativado depois. Deseja continuar?`
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
