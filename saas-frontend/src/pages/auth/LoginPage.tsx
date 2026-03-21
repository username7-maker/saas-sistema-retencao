import { zodResolver } from "@hookform/resolvers/zod";
import { Dumbbell, Sparkles } from "lucide-react";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { useAuth } from "../../hooks/useAuth";
import { Button, Input } from "../../components/ui2";

const loginSchema = z.object({
  gym_slug: z.string().min(3, "Informe o slug da academia"),
  email: z.string().email("Informe um e-mail valido"),
  password: z.string().min(8, "Minimo de 8 caracteres"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      gym_slug: "",
      email: "",
      password: "",
    },
  });

  const onSubmit = async (values: LoginFormValues) => {
    try {
      await login(values);
      const from = (location.state as { from?: string } | null)?.from ?? "/dashboard/executive";
      navigate(from, { replace: true });
    } catch {
      setError("root", { message: "Falha na autenticacao. Verifique credenciais." });
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-lovable-bg px-4 py-10">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-24 top-0 h-[420px] w-[420px] rounded-full bg-[hsl(var(--lovable-primary)/0.2)] blur-[150px]" />
        <div className="absolute right-[-120px] top-[12%] h-[340px] w-[340px] rounded-full bg-[hsl(var(--lovable-info)/0.15)] blur-[140px]" />
        <div className="absolute bottom-[-180px] left-[35%] h-[420px] w-[420px] rounded-full bg-[hsl(var(--lovable-success)/0.08)] blur-[170px]" />
      </div>

      <div className="relative w-full max-w-md rounded-[30px] border border-lovable-border bg-lovable-surface/96 p-8 shadow-panel backdrop-blur-2xl">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-[20px] bg-[linear-gradient(135deg,hsl(var(--lovable-primary)),hsl(var(--lovable-info)))] text-white shadow-[0_20px_40px_-22px_hsl(var(--lovable-primary)/0.95)]">
            <Dumbbell size={24} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-heading text-3xl font-bold tracking-tight text-lovable-ink">AI GYM OS</h1>
              <span className="inline-flex items-center gap-1 rounded-full bg-[hsl(var(--lovable-primary)/0.15)] px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[hsl(var(--lovable-primary))]">
                <Sparkles size={11} />
                Live
              </span>
            </div>
            <p className="mt-2 text-sm text-lovable-ink-muted">Acesso seguro ao sistema de retencao e BI.</p>
          </div>
        </div>

        <form className="mt-8 space-y-5" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <label className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">
              Academia (slug)
            </label>
            <Input
              {...register("gym_slug")}
              type="text"
              placeholder="academia-centro"
              className="h-12 rounded-2xl bg-lovable-bg-muted/75"
            />
            {errors.gym_slug ? <p className="mt-1 text-xs text-rose-400">{errors.gym_slug.message}</p> : null}
          </div>

          <div>
            <label className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">
              E-mail
            </label>
            <Input
              {...register("email")}
              type="email"
              placeholder="gestor@academia.com"
              className="h-12 rounded-2xl bg-lovable-bg-muted/75"
            />
            {errors.email ? <p className="mt-1 text-xs text-rose-400">{errors.email.message}</p> : null}
          </div>

          <div>
            <label className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">
              Senha
            </label>
            <Input
              {...register("password")}
              type="password"
              placeholder="••••••••"
              className="h-12 rounded-2xl bg-lovable-bg-muted/75"
            />
            {errors.password ? <p className="mt-1 text-xs text-rose-400">{errors.password.message}</p> : null}
          </div>

          {errors.root ? (
            <div className="rounded-2xl border border-[hsl(var(--lovable-danger)/0.22)] bg-[hsl(var(--lovable-danger)/0.08)] px-3 py-2 text-xs text-rose-300">
              {errors.root.message}
            </div>
          ) : null}

          <Button type="submit" disabled={isSubmitting} className="h-12 w-full rounded-2xl">
            {isSubmitting ? "Autenticando..." : "Entrar"}
          </Button>
        </form>
      </div>
    </div>
  );
}
