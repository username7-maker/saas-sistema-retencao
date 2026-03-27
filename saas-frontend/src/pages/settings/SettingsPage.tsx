import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import toast from "react-hot-toast";

import { useAuth } from "../../hooks/useAuth";
import { api } from "../../services/api";
import { ActuarConnectionTab } from "../../components/settings/ActuarConnectionTab";
import { WhatsAppConnectionTab } from "../../components/settings/WhatsAppConnectionTab";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../../components/ui2";

const forgotSchema = z.object({
  email: z.string().email("E-mail invalido"),
  gym_slug: z.string().min(3, "Slug invalido"),
});

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

type ForgotFormValues = z.infer<typeof forgotSchema>;
type ResetFormValues = z.infer<typeof resetSchema>;

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
      toast.success("Se o e-mail estiver cadastrado, voce recebera as instrucoes em breve.");
    } catch {
      toast.error("Nao foi possivel enviar o e-mail. Tente novamente.");
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex max-w-md flex-col gap-4">
      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
          E-mail
        </label>
        <Input {...register("email")} type="email" placeholder="seu@email.com" />
        {errors.email && <p className="mt-1 text-xs text-lovable-danger">{errors.email.message}</p>}
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
          Slug da academia
        </label>
        <Input {...register("gym_slug")} placeholder="minha-academia" />
        {errors.gym_slug && <p className="mt-1 text-xs text-lovable-danger">{errors.gym_slug.message}</p>}
        <p className="mt-1 text-xs text-lovable-ink-muted">O mesmo slug usado no login.</p>
      </div>

      <Button type="submit" variant="primary" disabled={isSubmitting} className="self-start">
        {isSubmitting ? "Enviando..." : "Enviar link de redefinicao"}
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
      toast.success("Senha redefinida com sucesso. Faca login com a nova senha.");
      reset();
    } catch {
      toast.error("Token invalido ou expirado. Solicite um novo link.");
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex max-w-md flex-col gap-4">
      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
          Token recebido por e-mail
        </label>
        <Input {...register("token")} placeholder="Cole o token aqui" />
        {errors.token && <p className="mt-1 text-xs text-lovable-danger">{errors.token.message}</p>}
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
          Nova senha
        </label>
        <Input {...register("new_password")} type="password" placeholder="Minimo 8 caracteres" />
        {errors.new_password && (
          <p className="mt-1 text-xs text-lovable-danger">{errors.new_password.message}</p>
        )}
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
          Confirmar nova senha
        </label>
        <Input {...register("confirm_password")} type="password" placeholder="Repita a nova senha" />
        {errors.confirm_password && (
          <p className="mt-1 text-xs text-lovable-danger">{errors.confirm_password.message}</p>
        )}
      </div>

      <Button type="submit" variant="primary" disabled={isSubmitting} className="self-start">
        {isSubmitting ? "Redefinindo..." : "Redefinir senha"}
      </Button>
    </form>
  );
}

export function SettingsPage() {
  const { user } = useAuth();
  const canManageWhatsapp = user?.role === "owner" || user?.role === "manager";
  const canManageActuar = user?.role === "owner" || user?.role === "manager";

  return (
    <section className="space-y-8">
      <header>
        <h2 className="font-heading text-3xl font-bold text-lovable-ink">Configuracoes</h2>
        <p className="text-sm text-lovable-ink-muted">
          Gerencie perfil, seguranca e conectores da academia.
        </p>
      </header>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList className="overflow-x-auto whitespace-nowrap">
          <TabsTrigger value="profile">Perfil</TabsTrigger>
          <TabsTrigger value="security">Seguranca</TabsTrigger>
          {canManageActuar && <TabsTrigger value="actuar">Actuar</TabsTrigger>}
          {canManageWhatsapp && <TabsTrigger value="whatsapp">WhatsApp</TabsTrigger>}
        </TabsList>

        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <CardTitle>Perfil</CardTitle>
              <p className="text-sm text-lovable-ink-muted">
                Informacoes da conta atualmente autenticada.
              </p>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div className="flex gap-2">
                  <span className="w-28 text-lovable-ink-muted">Nome</span>
                  <span className="font-medium text-lovable-ink">{user?.full_name}</span>
                </div>
                <div className="flex gap-2">
                  <span className="w-28 text-lovable-ink-muted">E-mail</span>
                  <span className="font-medium text-lovable-ink">{user?.email}</span>
                </div>
                <div className="flex gap-2">
                  <span className="w-28 text-lovable-ink-muted">Funcao</span>
                  <span className="font-medium capitalize text-lovable-ink">{user?.role}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Solicitar redefinicao de senha</CardTitle>
              <p className="text-sm text-lovable-ink-muted">
                Enviaremos um link de redefinicao para o seu e-mail. O link expira em 1 hora.
              </p>
            </CardHeader>
            <CardContent>
              <ForgotPasswordForm />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Redefinir senha com token</CardTitle>
              <p className="text-sm text-lovable-ink-muted">
                Se voce ja recebeu o token por e-mail, cole-o abaixo e defina sua nova senha.
              </p>
            </CardHeader>
            <CardContent>
              <ResetPasswordForm />
            </CardContent>
          </Card>
        </TabsContent>

        {canManageActuar && (
          <TabsContent value="actuar">
            <ActuarConnectionTab />
          </TabsContent>
        )}

        {canManageWhatsapp && (
          <TabsContent value="whatsapp">
            <WhatsAppConnectionTab />
          </TabsContent>
        )}
      </Tabs>
    </section>
  );
}
