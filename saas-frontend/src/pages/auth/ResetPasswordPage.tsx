import { zodResolver } from "@hookform/resolvers/zod";
import { Dumbbell, KeyRound } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { z } from "zod";

import { Button, Input } from "../../components/ui2";
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
    <div className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-lovable-bg px-4 py-10">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-24 top-0 h-[420px] w-[420px] rounded-full bg-[hsl(var(--lovable-primary)/0.2)] blur-[150px]" />
        <div className="absolute right-[-120px] top-[12%] h-[340px] w-[340px] rounded-full bg-[hsl(var(--lovable-info)/0.15)] blur-[140px]" />
      </div>

      <div className="relative w-full max-w-md rounded-[30px] border border-lovable-border bg-lovable-surface/96 p-5 shadow-panel backdrop-blur-2xl sm:p-8">
        <div className="flex items-center gap-3 sm:gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-[20px] bg-[linear-gradient(135deg,hsl(var(--lovable-primary)),hsl(var(--lovable-info)))] text-white shadow-[0_20px_40px_-22px_hsl(var(--lovable-primary)/0.95)]">
            <Dumbbell size={24} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-heading text-2xl font-bold tracking-tight text-lovable-ink sm:text-3xl">Nova senha</h1>
              <span className="inline-flex items-center gap-1 rounded-full bg-[hsl(var(--lovable-primary)/0.15)] px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[hsl(var(--lovable-primary))]">
                <KeyRound size={11} />
                Seguro
              </span>
            </div>
            <p className="mt-2 text-sm text-lovable-ink-muted">
              O token chega por fragmento seguro na URL e nao fica exposto em logs de navegacao.
            </p>
          </div>
        </div>

        <form className="mt-8 space-y-5" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <label className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">
              Token
            </label>
            <Input
              {...register("token")}
              type="text"
              placeholder="Token de redefinicao"
              className="h-12 rounded-2xl bg-lovable-bg-muted/75"
            />
            {errors.token ? <p className="mt-1 text-xs text-rose-400">{errors.token.message}</p> : null}
          </div>

          <div>
            <label className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">
              Nova senha
            </label>
            <Input
              {...register("new_password")}
              type="password"
              placeholder="Minimo de 8 caracteres"
              className="h-12 rounded-2xl bg-lovable-bg-muted/75"
            />
            {errors.new_password ? <p className="mt-1 text-xs text-rose-400">{errors.new_password.message}</p> : null}
          </div>

          <div>
            <label className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">
              Confirmar nova senha
            </label>
            <Input
              {...register("confirm_password")}
              type="password"
              placeholder="Repita a nova senha"
              className="h-12 rounded-2xl bg-lovable-bg-muted/75"
            />
            {errors.confirm_password ? <p className="mt-1 text-xs text-rose-400">{errors.confirm_password.message}</p> : null}
          </div>

          <Button type="submit" disabled={isSubmitting} className="h-12 w-full rounded-2xl">
            {isSubmitting ? "Redefinindo..." : "Salvar nova senha"}
          </Button>
        </form>

        <p className="mt-6 text-center text-xs text-lovable-ink-muted">
          Lembrou a senha?{" "}
          <Link to="/login" className="font-semibold text-[hsl(var(--lovable-primary))]">
            Voltar para o login
          </Link>
        </p>
      </div>
    </div>
  );
}
