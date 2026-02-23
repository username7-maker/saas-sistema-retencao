import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import toast from "react-hot-toast";

import { useAuth } from "../../hooks/useAuth";
import { api } from "../../services/api";
import { Button, Input } from "../../components/ui2";

// ─── Schemas ──────────────────────────────────────────────────────────────────

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
  .refine((d) => d.new_password === d.confirm_password, {
    path: ["confirm_password"],
    message: "As senhas não coincidem",
  });

type ForgotFormValues = z.infer<typeof forgotSchema>;
type ResetFormValues = z.infer<typeof resetSchema>;

// ─── Forgot password form ─────────────────────────────────────────────────────

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
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4 max-w-md">
      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
          E-mail
        </label>
        <Input {...register("email")} type="email" placeholder="seu@email.com" />
        {errors.email && <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>}
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
          Slug da Academia
        </label>
        <Input {...register("gym_slug")} placeholder="minha-academia" />
        {errors.gym_slug && <p className="mt-1 text-xs text-red-500">{errors.gym_slug.message}</p>}
        <p className="mt-1 text-xs text-lovable-ink-muted">
          O mesmo slug usado no login.
        </p>
      </div>

      <Button type="submit" variant="primary" disabled={isSubmitting} className="self-start">
        {isSubmitting ? "Enviando..." : "Enviar link de redefinição"}
      </Button>
    </form>
  );
}

// ─── Reset password form ──────────────────────────────────────────────────────

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
      toast.success("Senha redefinida com sucesso! Faça login com a nova senha.");
      reset();
    } catch {
      toast.error("Token inválido ou expirado. Solicite um novo link.");
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4 max-w-md">
      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
          Token recebido por e-mail
        </label>
        <Input {...register("token")} placeholder="Cole o token aqui" />
        {errors.token && <p className="mt-1 text-xs text-red-500">{errors.token.message}</p>}
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
          Nova senha
        </label>
        <Input {...register("new_password")} type="password" placeholder="Mínimo 8 caracteres" />
        {errors.new_password && <p className="mt-1 text-xs text-red-500">{errors.new_password.message}</p>}
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
          Confirmar nova senha
        </label>
        <Input {...register("confirm_password")} type="password" placeholder="Repita a nova senha" />
        {errors.confirm_password && (
          <p className="mt-1 text-xs text-red-500">{errors.confirm_password.message}</p>
        )}
      </div>

      <Button type="submit" variant="primary" disabled={isSubmitting} className="self-start">
        {isSubmitting ? "Redefinindo..." : "Redefinir senha"}
      </Button>
    </form>
  );
}

// ─── Main settings page ───────────────────────────────────────────────────────

export function SettingsPage() {
  const { user } = useAuth();

  return (
    <section className="space-y-8">
      <header>
        <h2 className="font-heading text-3xl font-bold text-lovable-ink">Configurações</h2>
        <p className="text-sm text-lovable-ink-muted">Gerencie suas preferências e segurança da conta.</p>
      </header>

      {/* Perfil */}
      <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-6">
        <h3 className="mb-4 text-base font-semibold text-lovable-ink">Perfil</h3>
        <div className="space-y-2 text-sm">
          <div className="flex gap-2">
            <span className="w-28 text-lovable-ink-muted">Nome</span>
            <span className="font-medium text-lovable-ink">{user?.full_name}</span>
          </div>
          <div className="flex gap-2">
            <span className="w-28 text-lovable-ink-muted">E-mail</span>
            <span className="font-medium text-lovable-ink">{user?.email}</span>
          </div>
          <div className="flex gap-2">
            <span className="w-28 text-lovable-ink-muted">Função</span>
            <span className="font-medium text-lovable-ink capitalize">{user?.role}</span>
          </div>
        </div>
      </div>

      {/* Solicitar link de redefinição */}
      <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-6">
        <h3 className="mb-1 text-base font-semibold text-lovable-ink">Solicitar redefinição de senha</h3>
        <p className="mb-4 text-sm text-lovable-ink-muted">
          Enviaremos um link de redefinição para o seu e-mail. O link expira em 1 hora.
        </p>
        <ForgotPasswordForm />
      </div>

      {/* Redefinir senha com token */}
      <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-6">
        <h3 className="mb-1 text-base font-semibold text-lovable-ink">Redefinir senha com token</h3>
        <p className="mb-4 text-sm text-lovable-ink-muted">
          Se você já recebeu o e-mail com o token, cole-o abaixo e defina sua nova senha.
        </p>
        <ResetPasswordForm />
      </div>
    </section>
  );
}
