import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";

import { useAuth } from "../../hooks/useAuth";
import { api } from "../../services/api";
import { userService } from "../../services/userService";
import { ActuarConnectionTab } from "../../components/settings/ActuarConnectionTab";
import { WhatsAppConnectionTab } from "../../components/settings/WhatsAppConnectionTab";
import { UserAvatar } from "../../components/common/UserAvatar";
import { Button, Card, CardContent, CardHeader, CardTitle, FormField, Input, Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui2";

const forgotSchema = z.object({
  email: z.string().email("E-mail inválido"),
  gym_slug: z.string().min(3, "Slug inválido"),
});

const resetSchema = z
  .object({
    token: z.string().min(10, "Token inválido"),
    new_password: z.string().min(8, "Senha deve ter pelo menos 8 caracteres"),
    confirm_password: z.string(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    path: ["confirm_password"],
    message: "As senhas não coincidem",
  });

const profileSchema = z.object({
  full_name: z.string().min(2, "Nome deve ter pelo menos 2 caracteres"),
  job_title: z.string().max(120, "Cargo muito longo").optional().or(z.literal("")),
  avatar_url: z.string().url("Informe uma URL válida para a foto").optional().or(z.literal("")),
});

type ForgotFormValues = z.infer<typeof forgotSchema>;
type ResetFormValues = z.infer<typeof resetSchema>;
type ProfileFormValues = z.infer<typeof profileSchema>;

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
      toast.success("Se o e-mail estiver cadastrado, você receberá as instruções em breve.");
    } catch {
      toast.error("Não foi possível enviar o e-mail. Tente novamente.");
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex max-w-md flex-col gap-4">
      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">E-mail</label>
        <Input {...register("email")} type="email" placeholder="seu@email.com" />
        {errors.email ? <p className="mt-1 text-xs text-lovable-danger">{errors.email.message}</p> : null}
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">Slug da academia</label>
        <Input {...register("gym_slug")} placeholder="minha-academia" />
        {errors.gym_slug ? <p className="mt-1 text-xs text-lovable-danger">{errors.gym_slug.message}</p> : null}
        <p className="mt-1 text-xs text-lovable-ink-muted">O mesmo slug usado no login.</p>
      </div>

      <Button type="submit" variant="primary" disabled={isSubmitting} className="self-start">
        {isSubmitting ? "Enviando..." : "Enviar link de redefinição"}
      </Button>
    </form>
  );
}

function ResetPasswordForm() {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ResetFormValues>({
    resolver: zodResolver(resetSchema),
  });

  async function onSubmit(values: ResetFormValues) {
    try {
      await api.post("/api/v1/auth/reset-password", {
        token: values.token,
        new_password: values.new_password,
      });
      toast.success("Senha redefinida com sucesso. Faça login com a nova senha.");
      reset();
    } catch {
      toast.error("Token inválido ou expirado. Solicite um novo link.");
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex max-w-md flex-col gap-4">
      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">Token recebido por e-mail</label>
        <Input {...register("token")} placeholder="Cole o token aqui" />
        {errors.token ? <p className="mt-1 text-xs text-lovable-danger">{errors.token.message}</p> : null}
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">Nova senha</label>
        <Input {...register("new_password")} type="password" placeholder="Mínimo 8 caracteres" />
        {errors.new_password ? <p className="mt-1 text-xs text-lovable-danger">{errors.new_password.message}</p> : null}
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">Confirmar nova senha</label>
        <Input {...register("confirm_password")} type="password" placeholder="Repita a nova senha" />
        {errors.confirm_password ? <p className="mt-1 text-xs text-lovable-danger">{errors.confirm_password.message}</p> : null}
      </div>

      <Button type="submit" variant="primary" disabled={isSubmitting} className="self-start">
        {isSubmitting ? "Redefinindo..." : "Redefinir senha"}
      </Button>
    </form>
  );
}

function ProfileForm() {
  const { user, refreshUser } = useAuth();
  const {
    register,
    handleSubmit,
    reset,
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
    onError: () => toast.error("Não foi possível atualizar o perfil."),
  });

  const avatarPreview = watch("avatar_url") || user?.avatar_url || null;
  const jobTitlePreview = watch("job_title") || user?.job_title || null;

  return (
    <div className="grid gap-6 lg:grid-cols-[280px,1fr]">
      <Card>
        <CardHeader>
          <CardTitle>Pré-visualização</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col items-center gap-3 text-center">
            <UserAvatar fullName={watch("full_name") || user?.full_name} avatarUrl={avatarPreview} size="lg" />
            <div>
              <p className="text-sm font-semibold text-lovable-ink">{watch("full_name") || user?.full_name}</p>
              <p className="text-xs uppercase tracking-[0.18em] text-lovable-ink-muted">{jobTitlePreview || user?.role}</p>
            </div>
          </div>
          <p className="text-xs text-lovable-ink-muted">Por enquanto a foto é configurada por URL. Upload de arquivo pode entrar na próxima iteração, se você quiser.</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Perfil</CardTitle>
          <p className="text-sm text-lovable-ink-muted">Edite nome, cargo exibido e foto usada na navegação e nas telas administrativas.</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit((values) => profileMutation.mutate(values))} className="grid gap-4 md:grid-cols-2">
            <FormField label="Nome completo" required error={errors.full_name?.message}>
              <Input {...register("full_name")} placeholder="Seu nome" />
            </FormField>

            <FormField label="Cargo exibido" error={errors.job_title?.message}>
              <Input {...register("job_title")} placeholder="Ex.: Head Coach, Recepção, Comercial" />
            </FormField>

            <div className="md:col-span-2">
              <FormField label="URL da foto" error={errors.avatar_url?.message}>
                <Input {...register("avatar_url")} placeholder="https://..." />
              </FormField>
            </div>

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

  return (
    <section className="space-y-8">
      <header>
        <h2 className="font-heading text-3xl font-bold text-lovable-ink">Configurações</h2>
        <p className="text-sm text-lovable-ink-muted">Gerencie perfil, segurança e conectores da academia.</p>
      </header>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList className="overflow-x-auto whitespace-nowrap">
          <TabsTrigger value="profile">Perfil</TabsTrigger>
          <TabsTrigger value="security">Segurança</TabsTrigger>
          {canManageActuar ? <TabsTrigger value="actuar">Actuar</TabsTrigger> : null}
          {canManageWhatsapp ? <TabsTrigger value="whatsapp">WhatsApp</TabsTrigger> : null}
        </TabsList>

        <TabsContent value="profile">
          <ProfileForm />
        </TabsContent>

        <TabsContent value="security" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Solicitar redefinição de senha</CardTitle>
              <p className="text-sm text-lovable-ink-muted">Enviaremos um link de redefinição para o seu e-mail. O link expira em 1 hora.</p>
            </CardHeader>
            <CardContent>
              <ForgotPasswordForm />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Redefinir senha com token</CardTitle>
              <p className="text-sm text-lovable-ink-muted">Se você já recebeu o token por e-mail, cole-o abaixo e defina sua nova senha.</p>
            </CardHeader>
            <CardContent>
              <ResetPasswordForm />
            </CardContent>
          </Card>
        </TabsContent>

        {canManageActuar ? (
          <TabsContent value="actuar">
            <ActuarConnectionTab />
          </TabsContent>
        ) : null}

        {canManageWhatsapp ? (
          <TabsContent value="whatsapp">
            <WhatsAppConnectionTab />
          </TabsContent>
        ) : null}
      </Tabs>
    </section>
  );
}
