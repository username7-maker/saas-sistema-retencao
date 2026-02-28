import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import toast from "react-hot-toast";

import { memberService, type MemberCreatePayload } from "../../services/memberService";
import { Button, Drawer, FormField, Input, Select } from "../../components/ui2";
import { todayIsoDate } from "./memberUtils";

const createSchema = z.object({
  full_name: z.string().min(2, "Nome obrigatorio"),
  email: z.string().email("Email invalido").optional().or(z.literal("")),
  phone: z.string().optional(),
  plan_name: z.enum(["Mensal", "Semestral", "Anual"]),
  monthly_fee: z.coerce.number().min(0, "Valor invalido"),
  join_date: z.string().min(1, "Data obrigatoria"),
  preferred_shift: z.string().optional(),
});

type CreateFormData = z.infer<typeof createSchema>;

export function AddMemberDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const initialValues: CreateFormData = {
    full_name: "",
    email: "",
    phone: "",
    plan_name: "Mensal",
    monthly_fee: 0,
    join_date: todayIsoDate(),
    preferred_shift: "",
  };

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateFormData>({
    resolver: zodResolver(createSchema),
    defaultValues: initialValues,
  });

  const createMutation = useMutation({
    mutationFn: (payload: MemberCreatePayload) => memberService.createMember(payload),
    onSuccess: () => {
      toast.success("Membro criado com sucesso!");
      void queryClient.invalidateQueries({ queryKey: ["members"] });
      reset(initialValues);
      onClose();
    },
    onError: () => toast.error("Erro ao criar membro"),
  });

  const onSubmit = (data: CreateFormData) => {
    createMutation.mutate({
      full_name: data.full_name.trim(),
      email: data.email || undefined,
      phone: data.phone || undefined,
      plan_name: data.plan_name,
      monthly_fee: data.monthly_fee,
      join_date: data.join_date,
      preferred_shift: data.preferred_shift || undefined,
    });
  };

  return (
    <Drawer
      open={open}
      onClose={() => {
        reset(initialValues);
        onClose();
      }}
      title="Adicionar Membro"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 p-4">
        <FormField label="Nome completo" required error={errors.full_name?.message}>
          <Input {...register("full_name")} placeholder="Nome do membro" />
        </FormField>

        <FormField label="Email" error={errors.email?.message}>
          <Input {...register("email")} type="email" placeholder="email@academia.com" />
        </FormField>

        <FormField label="Telefone">
          <Input {...register("phone")} placeholder="(11) 99999-9999" />
        </FormField>

        <FormField label="Plano" required error={errors.plan_name?.message}>
          <Select {...register("plan_name")}>
            <option value="Mensal">Mensal</option>
            <option value="Semestral">Semestral</option>
            <option value="Anual">Anual</option>
          </Select>
        </FormField>

        <FormField label="Mensalidade (R$)" error={errors.monthly_fee?.message}>
          <Input {...register("monthly_fee")} type="number" step="0.01" min="0" placeholder="0.00" />
        </FormField>

        <FormField label="Data de entrada" required error={errors.join_date?.message}>
          <Input {...register("join_date")} type="date" />
        </FormField>

        <FormField label="Turno preferido">
          <Select {...register("preferred_shift")}>
            <option value="">Nao definido</option>
            <option value="morning">Manha</option>
            <option value="afternoon">Tarde</option>
            <option value="evening">Noite</option>
          </Select>
        </FormField>

        <div className="flex gap-2 pt-2">
          <Button type="submit" variant="primary" disabled={isSubmitting} className="flex-1">
            {isSubmitting ? "Salvando..." : "Criar membro"}
          </Button>
          <Button type="button" variant="ghost" onClick={() => { reset(initialValues); onClose(); }}>
            Cancelar
          </Button>
        </div>
      </form>
    </Drawer>
  );
}
