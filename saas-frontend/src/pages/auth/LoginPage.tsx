import type React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, KeyRound, Sparkles } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import { useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { useAuth } from "../../hooks/useAuth";
import { Button, Input } from "../../components/ui2";
import { AuthLayout } from "../../components/layout/AuthLayout";
import { PRODUCT_NAME, PRODUCT_SHORT_TAGLINE } from "../../config/brand";
import { api } from "../../services/api";
import { resolvePostLoginRoute } from "../../utils/roleAccess";

/* Shared field wrapper for auth forms — label + optional inline action + error */
function AuthField({
  label,
  error,
  action,
  children,
}: {
  label: string;
  error?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <label className="block text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">
          {label}
        </label>
        {action}
      </div>
      {children}
      {error ? (
        <p className="mt-1.5 flex items-center gap-1.5 text-xs text-[hsl(var(--lovable-danger))]">
          <AlertCircle size={12} className="shrink-0" />
          {error}
        </p>
      ) : null}
    </div>
  );
}

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
    <AuthLayout>
      {/* Auth card */}
      <div className="relative overflow-hidden rounded-[24px] border border-white/[0.07] bg-[rgba(14,16,24,0.97)] p-5 shadow-[0_8px_40px_rgba(0,0,0,0.56)] backdrop-blur-xl sm:p-8">
        {/* Top glass shine */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 top-0 h-16 rounded-t-[24px]"
          style={{ background: "linear-gradient(180deg,rgba(255,255,255,0.04),transparent 60%)" }}
        />

        {/* Header */}
        <div className="relative flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <h2 className="font-heading text-2xl font-bold tracking-tight text-lovable-ink sm:text-3xl">
              {mode === "login" ? PRODUCT_NAME : "Recuperar acesso"}
            </h2>
            <span className="inline-flex items-center gap-1 rounded-full border border-[rgba(59,130,246,0.28)] bg-[rgba(59,130,246,0.10)] px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-blue-300">
              {mode === "login" ? <Sparkles size={11} /> : <KeyRound size={11} />}
              {mode === "login" ? "Core" : "Reset"}
            </span>
          </div>
          <p className="text-sm text-lovable-ink-muted">
            {mode === "login"
              ? `Acesso seguro ao sistema de ${PRODUCT_SHORT_TAGLINE.toLowerCase()}.`
              : "Informe academia e e-mail para receber o link de redefinição."}
          </p>
        </div>

        {mode === "login" ? (
          <form className="mt-7 space-y-4" onSubmit={loginForm.handleSubmit(onSubmit)}>
            <AuthField label="Academia (slug)" error={loginForm.formState.errors.gym_slug?.message}>
              <Input
                {...loginForm.register("gym_slug")}
                type="text"
                placeholder="academia-centro"
                className="h-12 rounded-2xl bg-white/[0.04]"
              />
            </AuthField>

            <AuthField label="E-mail" error={loginForm.formState.errors.email?.message}>
              <Input
                {...loginForm.register("email")}
                type="email"
                placeholder="gestor@academia.com"
                className="h-12 rounded-2xl bg-white/[0.04]"
              />
            </AuthField>

            <AuthField
              label="Senha"
              error={loginForm.formState.errors.password?.message}
              action={
                <button
                  type="button"
                  className="text-[11px] font-semibold text-blue-400 transition hover:text-blue-300"
                  onClick={() => setMode("forgot")}
                >
                  Esqueci minha senha
                </button>
              }
            >
              <Input
                {...loginForm.register("password")}
                type="password"
                placeholder="••••••••"
                className="h-12 rounded-2xl bg-white/[0.04]"
              />
            </AuthField>

            {loginForm.formState.errors.root ? (
              <div className="flex items-start gap-2 rounded-2xl border border-[rgba(255,59,59,0.22)] bg-[rgba(255,59,59,0.07)] px-3 py-2.5">
                <AlertCircle size={14} className="mt-0.5 shrink-0 text-[hsl(var(--lovable-danger))]" />
                <p className="text-xs text-[hsl(var(--lovable-danger))]">
                  {loginForm.formState.errors.root.message}
                </p>
              </div>
            ) : null}

            <Button type="submit" disabled={loginForm.formState.isSubmitting} className="h-12 w-full rounded-2xl">
              {loginForm.formState.isSubmitting ? "Autenticando..." : "Entrar"}
            </Button>
          </form>
        ) : (
          <form className="mt-7 space-y-4" onSubmit={forgotForm.handleSubmit(onForgotSubmit)}>
            <AuthField label="Academia (slug)" error={forgotForm.formState.errors.gym_slug?.message}>
              <Input
                {...forgotForm.register("gym_slug")}
                type="text"
                placeholder="academia-centro"
                className="h-12 rounded-2xl bg-white/[0.04]"
              />
            </AuthField>

            <AuthField label="E-mail" error={forgotForm.formState.errors.email?.message}>
              <Input
                {...forgotForm.register("email")}
                type="email"
                placeholder="gestor@academia.com"
                className="h-12 rounded-2xl bg-white/[0.04]"
              />
            </AuthField>

            <Button type="submit" disabled={forgotForm.formState.isSubmitting} className="h-12 w-full rounded-2xl">
              {forgotForm.formState.isSubmitting ? "Enviando..." : "Enviar link de redefinição"}
            </Button>
            <Button type="button" variant="ghost" className="h-11 w-full rounded-2xl" onClick={() => setMode("login")}>
              Voltar para o login
            </Button>
          </form>
        )}
      </div>
    </AuthLayout>
  );
}
