import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, CheckCircle2, KeyRound } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { z } from "zod";

import { Button, Input } from "../../components/ui2";
import { AuthLayout } from "../../components/layout/AuthLayout";
import { PRODUCT_NAME } from "../../config/brand";
import { api } from "../../services/api";

const resetSchema = z
  .object({
    token: z.string().min(10, "Token invalido"),
    new_password: z.string().min(8, "Senha deve ter pelo menos 8 caracteres"),
    confirm_password: z.string(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    path: ["confirm_password"],
    message: "As senhas nao coincidem",
  });

type ResetFormValues = z.infer<typeof resetSchema>;

function resolveTokenFromLocation(location: ReturnType<typeof useLocation>): string {
  const hash = location.hash.startsWith("#") ? location.hash.slice(1) : location.hash;
  const hashParams = new URLSearchParams(hash);
  const queryParams = new URLSearchParams(location.search);
  return hashParams.get("token") || queryParams.get("token") || "";
}

export function ResetPasswordPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<ResetFormValues>({
    resolver: zodResolver(resetSchema),
    defaultValues: {
      token: "",
      new_password: "",
      confirm_password: "",
    },
  });

  useEffect(() => {
    setValue("token", resolveTokenFromLocation(location), { shouldValidate: true });
  }, [location, setValue]);

  const onSubmit = async (values: ResetFormValues) => {
    try {
      await api.post("/api/v1/auth/reset-password", {
        token: values.token,
        new_password: values.new_password,
      });
      toast.success("Senha redefinida com sucesso. Entre com a nova senha.");
      navigate("/login", { replace: true });
    } catch {
      toast.error("Token invalido ou expirado. Solicite um novo link.");
    }
  };

  return (
    <AuthLayout>
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
              Nova senha
            </h2>
            <span className="inline-flex items-center gap-1 rounded-full border border-[rgba(139,92,246,0.28)] bg-[rgba(139,92,246,0.10)] px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-violet-300">
              <KeyRound size={11} />
              {PRODUCT_NAME}
            </span>
          </div>
          <p className="text-sm text-lovable-ink-muted">
            O token chega por fragmento seguro na URL e não fica exposto em logs de navegação.
          </p>
        </div>

        <form className="relative mt-7 space-y-4" onSubmit={handleSubmit(onSubmit)}>
          {/* Token field — hidden visually if auto-filled from URL; still part of the form */}
          <div>
            <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">
              Token
            </label>
            <Input
              {...register("token")}
              type="text"
              placeholder="Token de redefinição"
              className="h-12 rounded-2xl bg-white/[0.04]"
            />
            {errors.token ? (
              <p className="mt-1.5 flex items-center gap-1.5 text-xs text-[hsl(var(--lovable-danger))]">
                <AlertCircle size={12} className="shrink-0" />
                {errors.token.message}
              </p>
            ) : null}
          </div>

          <div>
            <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">
              Nova senha
            </label>
            <Input
              {...register("new_password")}
              type="password"
              placeholder="Mínimo de 8 caracteres"
              className="h-12 rounded-2xl bg-white/[0.04]"
            />
            {errors.new_password ? (
              <p className="mt-1.5 flex items-center gap-1.5 text-xs text-[hsl(var(--lovable-danger))]">
                <AlertCircle size={12} className="shrink-0" />
                {errors.new_password.message}
              </p>
            ) : null}
          </div>

          <div>
            <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">
              Confirmar nova senha
            </label>
            <Input
              {...register("confirm_password")}
              type="password"
              placeholder="Repita a nova senha"
              className="h-12 rounded-2xl bg-white/[0.04]"
            />
            {errors.confirm_password ? (
              <p className="mt-1.5 flex items-center gap-1.5 text-xs text-[hsl(var(--lovable-danger))]">
                <AlertCircle size={12} className="shrink-0" />
                {errors.confirm_password.message}
              </p>
            ) : errors.confirm_password === undefined && !errors.new_password && !errors.token ? null : (
              <p className="mt-1.5 flex items-center gap-1.5 text-xs text-emerald-400">
                <CheckCircle2 size={12} className="shrink-0" />
                Senhas conferem
              </p>
            )}
          </div>

          <Button type="submit" disabled={isSubmitting} className="h-12 w-full rounded-2xl">
            {isSubmitting ? "Redefinindo..." : "Salvar nova senha"}
          </Button>
        </form>

        <p className="relative mt-5 text-center text-xs text-lovable-ink-muted">
          Lembrou a senha?{" "}
          <Link to="/login" className="font-semibold text-blue-400 transition hover:text-blue-300">
            Voltar para o login
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}
