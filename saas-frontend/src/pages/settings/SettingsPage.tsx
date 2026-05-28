import { useEffect, type ChangeEvent } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";

import { useAuth } from "../../hooks/useAuth";
import { api } from "../../services/api";
import { userService } from "../../services/userService";
import { ActuarConnectionTab } from "../../components/settings/ActuarConnectionTab";
import { AiServiceAgentSettingsTab } from "../../components/settings/AiServiceAgentSettingsTab";
import { AutopilotSettingsTab } from "../../components/settings/AutopilotSettingsTab";
import { KommoConnectionTab } from "../../components/settings/KommoConnectionTab";
import { MovementVideoSettingsTab } from "../../components/settings/MovementVideoSettingsTab";
import { PersonalAiSettingsTab } from "../../components/settings/PersonalAiSettingsTab";
import { StudentPersonalAiSettingsTab } from "../../components/settings/StudentPersonalAiSettingsTab";
import { WhatsAppConnectionTab } from "../../components/settings/WhatsAppConnectionTab";
import { UserAvatar } from "../../components/common/UserAvatar";
import { Button, Card, CardContent, CardHeader, CardTitle, FormField, Input, Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui2";

const forgotSchema = z.object({
  email: z.string().email("E-mail invalido"),
  gym_slug: z.string().min(3, "Slug invalido"),
});

const passwordSchema = z
  .object({
    current_password: z.string().min(8, "Informe sua senha atual"),
    new_password: z.string().min(8, "A nova senha deve ter pelo menos 8 caracteres"),
    confirm_password: z.string().min(8, "Confirme a nova senha"),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    path: ["confirm_password"],
    message: "As senhas nao coincidem",
  });

const profileSchema = z.object({
  full_name: z.string().min(2, "Nome deve ter pelo menos 2 caracteres"),
  job_title: z.string().max(120, "Cargo muito longo").optional().or(z.literal("")),
  avatar_url: z
    .string()
    .refine((value) => !value || isValidAvatarSource(value), "Informe uma URL valida ou envie uma imagem")
    .optional(),
});

type ForgotFormValues = z.infer<typeof forgotSchema>;
type PasswordFormValues = z.infer<typeof passwordSchema>;
type ProfileFormValues = z.infer<typeof profileSchema>;

const MAX_AVATAR_UPLOAD_BYTES = 1_500_000;
const AVATAR_UPLOAD_TYPES = ["image/jpeg", "image/png", "image/webp"];

function isValidAvatarSource(value: string) {
  if (!value) return true;
  if (/^data:image\/(jpeg|png|webp);base64,/i.test(value)) return true;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function getErrorDetail(error: unknown, fallback: string) {
  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error &&
    typeof (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail === "string"
  ) {
    return (error as { response: { data: { detail: string } } }).response.data.detail;
  }
  return fallback;
}

function ForgotPasswordForm() {
  const { user } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotFormValues>({
    resolver: zodResolver(forgotSchema),
    defaultValues: { email: user?.email ?? "" },
  });

  async function onSubmit(values: ForgotFormValues) {
    try {
      await api.post("/api/v1/auth/forgot-password", values);
      toast.success("Se o e-mail estiver cadastrado, enviaremos as instrucoes.");
    } catch (error: unknown) {
      toast.error(getErrorDetail(error, "Nao foi possivel enviar o e-mail. Solicite reset ao administrador."));
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="grid max-w-2xl gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
      <FormField label="E-mail" required error={errors.email?.message}>
        <Input {...register("email")} type="email" placeholder="seu@email.com" />
      </FormField>

      <FormField label="Slug da academia" required error={errors.gym_slug?.message}>
        <Input {...register("gym_slug")} placeholder="minha-academia" />
      </FormField>

      <Button type="submit" variant="primary" disabled={isSubmitting} className="md:mb-0.5">
        {isSubmitting ? "Enviando..." : "Enviar link"}
      </Button>
    </form>
  );
}

function ChangePasswordForm() {
  const { logout } = useAuth();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      current_password: "",
      new_password: "",
      confirm_password: "",
    },
  });

  const passwordMutation = useMutation({
    mutationFn: (values: PasswordFormValues) =>
      userService.updateMyPassword({
        current_password: values.current_password,
        new_password: values.new_password,
      }),
    onSuccess: async () => {
      reset();
      toast.success("Senha atualizada. Entre novamente com a nova senha.");
      await logout();
    },
    onError: (error: unknown) => {
      toast.error(getErrorDetail(error, "Nao foi possivel alterar a senha."));
    },
  });

  return (
    <form onSubmit={handleSubmit((values) => passwordMutation.mutate(values))} className="grid max-w-3xl gap-4 md:grid-cols-3 md:items-end">
      <FormField label="Senha atual" required error={errors.current_password?.message}>
        <Input {...register("current_password")} type="password" placeholder="Senha atual" autoComplete="current-password" />
      </FormField>

      <FormField label="Nova senha" required error={errors.new_password?.message}>
        <Input {...register("new_password")} type="password" placeholder="Minimo de 8 caracteres" autoComplete="new-password" />
      </FormField>

      <FormField label="Confirmar nova senha" required error={errors.confirm_password?.message}>
        <Input {...register("confirm_password")} type="password" placeholder="Repita a nova senha" autoComplete="new-password" />
      </FormField>

      <div className="md:col-span-3 flex justify-end">
        <Button type="submit" variant="primary" disabled={isSubmitting || passwordMutation.isPending}>
          {passwordMutation.isPending ? "Alterando..." : "Alterar senha"}
        </Button>
      </div>
    </form>
  );
}

function ProfileForm() {
  const { user, refreshUser } = useAuth();
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user?.full_name ?? "",
      job_title: user?.job_title ?? "",
      avatar_url: user?.avatar_url ?? "",
    },
  });

  useEffect(() => {
    reset({
      full_name: user?.full_name ?? "",
      job_title: user?.job_title ?? "",
      avatar_url: user?.avatar_url ?? "",
    });
  }, [reset, user?.avatar_url, user?.full_name, user?.job_title]);

  const profileMutation = useMutation({
    mutationFn: (values: ProfileFormValues) =>
      userService.updateMyProfile({
        full_name: values.full_name,
        job_title: values.job_title?.trim() || null,
        avatar_url: values.avatar_url?.trim() || null,
      }),
    onSuccess: async () => {
      await refreshUser();
      toast.success("Perfil atualizado com sucesso.");
    },
    onError: () => toast.error("Nao foi possivel atualizar o perfil."),
  });

  const avatarUploadMutation = useMutation({
    mutationFn: (file: File) => userService.uploadMyAvatar(file),
    onSuccess: async (updatedUser) => {
      setValue("avatar_url", updatedUser.avatar_url ?? "", { shouldDirty: false, shouldValidate: true });
      await refreshUser();
      toast.success("Foto do perfil enviada com sucesso.");
    },
    onError: () => toast.error("Nao foi possivel enviar a foto do perfil."),
  });

  function handleAvatarFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    if (!AVATAR_UPLOAD_TYPES.includes(file.type)) {
      toast.error("Envie uma imagem JPG, PNG ou WebP.");
      return;
    }

    if (file.size > MAX_AVATAR_UPLOAD_BYTES) {
      toast.error("A foto precisa ter no maximo 1,5 MB.");
      return;
    }

    avatarUploadMutation.mutate(file);
  }

  const avatarPreview = watch("avatar_url") || user?.avatar_url || null;
  const jobTitlePreview = watch("job_title") || user?.job_title || null;

  return (
    <div className="grid gap-5 lg:grid-cols-[240px,1fr]">
      <Card>
        <CardHeader>
          <CardTitle>Perfil atual</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col items-center gap-3 text-center">
            <UserAvatar fullName={watch("full_name") || user?.full_name} avatarUrl={avatarPreview} size="lg" />
            <div>
              <p className="text-sm font-semibold text-lovable-ink">{watch("full_name") || user?.full_name}</p>
              <p className="text-xs uppercase tracking-[0.18em] text-lovable-ink-muted">{jobTitlePreview || user?.role}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Editar perfil</CardTitle>
          <p className="text-sm text-lovable-ink-muted">Nome, cargo exibido e foto usados nas telas administrativas.</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit((values) => profileMutation.mutate(values))} className="grid gap-4 md:grid-cols-2">
            <FormField label="Nome completo" required error={errors.full_name?.message}>
              <Input {...register("full_name")} placeholder="Seu nome" />
            </FormField>

            <FormField label="Cargo exibido" error={errors.job_title?.message}>
              <Input {...register("job_title")} placeholder="Ex.: Head Coach, Recepcao, Comercial" />
            </FormField>

            <div className="md:col-span-2">
              <FormField label="Enviar foto do perfil">
                <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-dashed border-lovable-border bg-lovable-surface-soft p-4">
                  <input
                    id="profile-avatar-upload"
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    className="sr-only"
                    onChange={handleAvatarFileChange}
                    disabled={avatarUploadMutation.isPending}
                  />
                  <label
                    htmlFor="profile-avatar-upload"
                    className="inline-flex h-10 cursor-pointer items-center justify-center rounded-xl border border-lovable-border bg-lovable-surface px-4 text-sm font-semibold text-lovable-ink transition hover:border-lovable-border-strong hover:bg-lovable-surface-soft"
                  >
                    {avatarUploadMutation.isPending ? "Enviando..." : "Escolher imagem"}
                  </label>
                  <p className="text-xs text-lovable-ink-muted">JPG, PNG ou WebP ate 1,5 MB.</p>
                </div>
              </FormField>
            </div>

            <details className="md:col-span-2 rounded-2xl border border-lovable-border bg-lovable-surface-soft/50 p-3">
              <summary className="cursor-pointer text-sm font-semibold text-lovable-ink">Origem alternativa da foto</summary>
              <div className="mt-3">
                <FormField label="URL da foto (fallback)" error={errors.avatar_url?.message}>
                  <Input {...register("avatar_url")} placeholder="https://... ou deixe preenchido apos upload" />
                </FormField>
              </div>
            </details>

            <div className="md:col-span-2 flex justify-end">
              <Button type="submit" variant="primary" disabled={profileMutation.isPending}>
                {profileMutation.isPending ? "Salvando..." : "Salvar perfil"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

export function SettingsPage() {
  const { user } = useAuth();
  const canManageWhatsapp = user?.role === "owner" || user?.role === "manager";
  const canManageActuar = user?.role === "owner" || user?.role === "manager";
  const canManageKommo = user?.role === "owner" || user?.role === "manager";
  const canManageAutopilot = user?.role === "owner" || user?.role === "manager";
  const canManageAiServiceAgent = user?.role === "owner" || user?.role === "manager";
  const canManagePersonalAi = user?.role === "owner" || user?.role === "manager";
  const canManageMovementVideo = user?.role === "owner" || user?.role === "manager";
  const canManageStudentPersonalAi = user?.role === "owner" || user?.role === "manager";

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-lovable-ink">Configuracoes</h2>
        <p className="text-sm text-lovable-ink-muted">Perfil, seguranca e conectores operacionais da academia.</p>
      </header>

      <Tabs defaultValue="profile" className="space-y-5">
        <TabsList className="max-w-full overflow-x-auto whitespace-nowrap">
          <TabsTrigger value="profile">Perfil</TabsTrigger>
          <TabsTrigger value="security">Seguranca</TabsTrigger>
          {canManageWhatsapp ? <TabsTrigger value="whatsapp">WhatsApp</TabsTrigger> : null}
          {canManageActuar ? <TabsTrigger value="actuar">Actuar</TabsTrigger> : null}
          {canManageKommo ? <TabsTrigger value="kommo">Kommo</TabsTrigger> : null}
          {canManageAutopilot ? <TabsTrigger value="autopilot">Autopilot</TabsTrigger> : null}
          {canManageAiServiceAgent ? <TabsTrigger value="ai-service-agent">Agent</TabsTrigger> : null}
          {canManagePersonalAi ? <TabsTrigger value="personal-ai">Coach</TabsTrigger> : null}
          {canManageMovementVideo ? <TabsTrigger value="movement-video-ai">Motion</TabsTrigger> : null}
          {canManageStudentPersonalAi ? <TabsTrigger value="student-personal-ai">Aluno</TabsTrigger> : null}
        </TabsList>

        <TabsContent value="profile">
          <ProfileForm />
        </TabsContent>

        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle>Alterar minha senha</CardTitle>
              <p className="text-sm text-lovable-ink-muted">
                Use quando voce esta logado. A sessao sera encerrada para entrar novamente com a nova senha.
              </p>
            </CardHeader>
            <CardContent>
              <ChangePasswordForm />
            </CardContent>
          </Card>

          <Card className="mt-4">
            <CardHeader>
              <CardTitle>Recuperacao por e-mail</CardTitle>
              <p className="text-sm text-lovable-ink-muted">
                Envia um link de redefinicao para quem nao consegue entrar. Se o provedor de e-mail bloquear o envio, use a troca acima ou gere senha provisoria em Usuarios.
              </p>
            </CardHeader>
            <CardContent>
              <ForgotPasswordForm />
            </CardContent>
          </Card>
        </TabsContent>

        {canManageWhatsapp ? (
          <TabsContent value="whatsapp">
            <WhatsAppConnectionTab />
          </TabsContent>
        ) : null}

        {canManageActuar ? (
          <TabsContent value="actuar">
            <ActuarConnectionTab />
          </TabsContent>
        ) : null}

        {canManageKommo ? (
          <TabsContent value="kommo">
            <KommoConnectionTab />
          </TabsContent>
        ) : null}

        {canManageAutopilot ? (
          <TabsContent value="autopilot">
            <AutopilotSettingsTab />
          </TabsContent>
        ) : null}

        {canManageAiServiceAgent ? (
          <TabsContent value="ai-service-agent">
            <AiServiceAgentSettingsTab />
          </TabsContent>
        ) : null}

        {canManagePersonalAi ? (
          <TabsContent value="personal-ai">
            <PersonalAiSettingsTab />
          </TabsContent>
        ) : null}

        {canManageMovementVideo ? (
          <TabsContent value="movement-video-ai">
            <MovementVideoSettingsTab />
          </TabsContent>
        ) : null}

        {canManageStudentPersonalAi ? (
          <TabsContent value="student-personal-ai">
            <StudentPersonalAiSettingsTab />
          </TabsContent>
        ) : null}
      </Tabs>
    </section>
  );
}
