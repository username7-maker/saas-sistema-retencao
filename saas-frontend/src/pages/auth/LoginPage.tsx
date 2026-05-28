import { zodResolver } from "@hookform/resolvers/zod";
import { KeyRound, Sparkles } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import { useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { useAuth } from "../../hooks/useAuth";
import { Button, Input } from "../../components/ui2";
import { BRAND_ASSETS, PRODUCT_NAME, PRODUCT_SHORT_TAGLINE } from "../../config/brand";
import { api } from "../../services/api";
import { resolvePostLoginRoute } from "../../utils/roleAccess";

const loginSchema = z.object({
  gym_slug: z.string().min(3, "Informe o slug da academia"),
  email: z.string().email("Informe um e-mail valido"),
  password: z.string().min(8, "Minimo de 8 caracteres"),
});

const forgotSchema = z.object({
  gym_slug: z.string().min(3, "Informe o slug da academia"),
  email: z.string().email("Informe um e-mail valido"),
});

type LoginFormValues = z.infer<typeof loginSchema>;
type ForgotFormValues = z.infer<typeof forgotSchema>;

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<"login" | "forgot">("login");

  const loginForm = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      gym_slug: "",
      email: "",
      password: "",
    },
  });

  const forgotForm = useForm<ForgotFormValues>({
    resolver: zodResolver(forgotSchema),
    defaultValues: {
      gym_slug: "",
      email: "",
    },
  });

  const onSubmit = async (values: LoginFormValues) => {
    try {
      const currentUser = await login(values);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(resolvePostLoginRoute(currentUser.role, from), { replace: true });
    } catch {
      loginForm.setError("root", { message: "Falha na autenticacao. Verifique credenciais." });
    }
  };

  const onForgotSubmit = async (values: ForgotFormValues) => {
    try {
      await api.post("/api/v1/auth/forgot-password", values);
      toast.success("Se o e-mail estiver cadastrado, enviaremos as instrucoes.");
      setMode("login");
    } catch (error: unknown) {
      const detail =
        typeof error === "object" &&
        error !== null &&
        "response" in error &&
        typeof (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail === "string"
          ? (error as { response: { data: { detail: string } } }).response.data.detail
          : "Nao foi possivel enviar o e-mail. Solicite reset ao administrador.";
      toast.error(detail);
    }
  };

  return (
    <div className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-lovable-bg px-4 py-10">
      <div className="relative w-full max-w-md overflow-hidden rounded-[24px] border border-lovable-border bg-lovable-surface/96 p-5 shadow-panel backdrop-blur-xl sm:p-8">
        <div className="flex items-center gap-3 sm:gap-4">
          <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-2xl border border-lovable-border/70 bg-lovable-bg-muted">
            <img src={BRAND_ASSETS.markDark} alt="" className="h-9 w-9 object-contain" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-heading text-2xl font-bold tracking-tight text-lovable-ink sm:text-3xl">{PRODUCT_NAME}</h1>
              <span className="inline-flex items-center gap-1 rounded-full bg-[hsl(var(--lovable-primary)/0.12)] px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[hsl(var(--lovable-primary))]">
                {mode === "login" ? <Sparkles size={11} /> : <KeyRound size={11} />}
                Core
              </span>
            </div>
            <p className="mt-2 text-sm text-lovable-ink-muted">
              {mode === "login"
                ? `Acesso seguro ao sistema de ${PRODUCT_SHORT_TAGLINE.toLowerCase()}.`
                : "Informe academia e e-mail para receber o link de redefinicao."}
            </p>
          </div>
        </div>

        {mode === "login" ? (
          <form className="mt-8 space-y-5" onSubmit={loginForm.handleSubmit(onSubmit)}>
            <div>
              <label className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">
                Academia (slug)
              </label>
              <Input
                {...loginForm.register("gym_slug")}
                type="text"
                placeholder="academia-centro"
                className="h-12 rounded-2xl bg-lovable-bg-muted/75"
              />
              {loginForm.formState.errors.gym_slug ? (
                <p className="mt-1 text-xs text-rose-400">{loginForm.formState.errors.gym_slug.message}</p>
              ) : null}
            </div>

            <div>
              <label className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">
                E-mail
              </label>
              <Input
                {...loginForm.register("email")}
                type="email"
                placeholder="gestor@academia.com"
                className="h-12 rounded-2xl bg-lovable-bg-muted/75"
              />
              {loginForm.formState.errors.email ? (
                <p className="mt-1 text-xs text-rose-400">{loginForm.formState.errors.email.message}</p>
              ) : null}
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between gap-3">
                <label className="block text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">
                  Senha
                </label>
                <button
                  type="button"
                  className="text-xs font-semibold text-[hsl(var(--lovable-primary))] transition hover:text-lovable-ink"
                  onClick={() => setMode("forgot")}
                >
                  Esqueci minha senha
                </button>
              </div>
              <Input
                {...loginForm.register("password")}
                type="password"
                placeholder="********"
                className="h-12 rounded-2xl bg-lovable-bg-muted/75"
              />
              {loginForm.formState.errors.password ? (
                <p className="mt-1 text-xs text-rose-400">{loginForm.formState.errors.password.message}</p>
              ) : null}
            </div>

            {loginForm.formState.errors.root ? (
              <div className="rounded-2xl border border-[hsl(var(--lovable-danger)/0.22)] bg-[hsl(var(--lovable-danger)/0.08)] px-3 py-2 text-xs text-rose-300">
                {loginForm.formState.errors.root.message}
              </div>
            ) : null}

            <Button type="submit" disabled={loginForm.formState.isSubmitting} className="h-12 w-full rounded-2xl">
              {loginForm.formState.isSubmitting ? "Autenticando..." : "Entrar"}
            </Button>
          </form>
        ) : (
          <form className="mt-8 space-y-5" onSubmit={forgotForm.handleSubmit(onForgotSubmit)}>
            <div>
              <label className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">
                Academia (slug)
              </label>
              <Input
                {...forgotForm.register("gym_slug")}
                type="text"
                placeholder="academia-centro"
                className="h-12 rounded-2xl bg-lovable-bg-muted/75"
              />
              {forgotForm.formState.errors.gym_slug ? (
                <p className="mt-1 text-xs text-rose-400">{forgotForm.formState.errors.gym_slug.message}</p>
              ) : null}
            </div>

            <div>
              <label className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">
                E-mail
              </label>
              <Input
                {...forgotForm.register("email")}
                type="email"
                placeholder="gestor@academia.com"
                className="h-12 rounded-2xl bg-lovable-bg-muted/75"
              />
              {forgotForm.formState.errors.email ? (
                <p className="mt-1 text-xs text-rose-400">{forgotForm.formState.errors.email.message}</p>
              ) : null}
            </div>

            <Button type="submit" disabled={forgotForm.formState.isSubmitting} className="h-12 w-full rounded-2xl">
              {forgotForm.formState.isSubmitting ? "Enviando..." : "Enviar link de redefinicao"}
            </Button>
            <Button type="button" variant="ghost" className="h-11 w-full rounded-2xl" onClick={() => setMode("login")}>
              Voltar para o login
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
