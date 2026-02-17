import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { useAuth } from "../../hooks/useAuth";

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
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_#d6f5eb_0%,_#f8fffd_30%,_#eff6ff_100%)] px-4">
      <div className="w-full max-w-md rounded-3xl border border-brand-100 bg-white/90 p-8 shadow-panel">
        <h1 className="font-heading text-3xl font-bold text-brand-700">AI GYM OS</h1>
        <p className="mt-2 text-sm text-slate-500">Acesso seguro ao sistema de retencao e BI.</p>

        <form className="mt-8 space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-slate-500">Academia (slug)</label>
            <input
              {...register("gym_slug")}
              type="text"
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none ring-brand-300 focus:ring"
              placeholder="academia-centro"
            />
            {errors.gym_slug && <p className="mt-1 text-xs text-rose-500">{errors.gym_slug.message}</p>}
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-slate-500">E-mail</label>
            <input
              {...register("email")}
              type="email"
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none ring-brand-300 focus:ring"
              placeholder="gestor@academia.com"
            />
            {errors.email && <p className="mt-1 text-xs text-rose-500">{errors.email.message}</p>}
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-slate-500">Senha</label>
            <input
              {...register("password")}
              type="password"
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none ring-brand-300 focus:ring"
              placeholder="••••••••"
            />
            {errors.password && <p className="mt-1 text-xs text-rose-500">{errors.password.message}</p>}
          </div>

          {errors.root && <p className="rounded-lg bg-rose-50 p-2 text-xs text-rose-500">{errors.root.message}</p>}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-xl bg-brand-500 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Autenticando..." : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}
