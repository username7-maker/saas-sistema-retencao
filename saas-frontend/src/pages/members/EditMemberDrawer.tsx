import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import toast from "react-hot-toast";

import { memberService, type MemberUpdatePayload } from "../../services/memberService";
import type { Member } from "../../types";
import { Button, Drawer, FormField, Input, Select } from "../../components/ui2";

const editSchema = z.object({
  full_name: z.string().min(2, "Nome obrigatório"),
  email: z.string().email("E-mail inválido").optional().or(z.literal("")),
  phone: z.string().optional(),
  plan_name: z.string().min(1, "Plano obrigatório"),
  monthly_fee: z.coerce.number().min(0).optional(),
  status: z.enum(["active", "paused", "cancelled"]),
  preferred_shift: z.string().optional(),
});

type EditFormData = z.infer<typeof editSchema>;

export function EditMemberDrawer({
  member,
  open,
  onClose,
}: {
  member: Member | null;
  open: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<EditFormData>({
    resolver: zodResolver(editSchema),
    values: member
      ? {
          full_name: member.full_name,
          email: member.email ?? "",
          phone: member.phone ?? "",
          plan_name: member.plan_name,
          monthly_fee: member.monthly_fee,
          status: member.status,
          preferred_shift: member.preferred_shift ?? "",
        }
      : undefined,
  });

  const updateMutation = useMutation({
    mutationFn: (data: MemberUpdatePayload) => memberService.updateMember(member!.id, data),
    onSuccess: () => {
      toast.success("Membro atualizado com sucesso!");
      void queryClient.invalidateQueries({ queryKey: ["members"] });
      onClose();
    },
    onError: () => toast.error("Erro ao atualizar membro"),
  });

  const onSubmit = (data: EditFormData) => {
    updateMutation.mutate({
      ...data,
      email: data.email || undefined,
      phone: data.phone || undefined,
      preferred_shift: data.preferred_shift || undefined,
    });
  };

  return (
    <Drawer open={open} onClose={() => { reset(); onClose(); }} title="Editar Membro">
      {member ? (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 p-4">
          <FormField label="Nome completo" required error={errors.full_name?.message}>
            <Input {...register("full_name")} placeholder="Nome do membro" />
          </FormField>

          <FormField label="E-mail" error={errors.email?.message}>
            <Input {...register("email")} type="email" placeholder="email@academia.com" />
          </FormField>

          <FormField label="Telefone">
            <Input {...register("phone")} placeholder="(11) 99999-9999" />
          </FormField>

          <FormField label="Plano" required error={errors.plan_name?.message}>
            <Input {...register("plan_name")} placeholder="Ex: Mensal, Trimestral" />
          </FormField>

          <FormField label="Mensalidade (R$)">
            <Input {...register("monthly_fee")} type="number" step="0.01" placeholder="0.00" />
          </FormField>

          <FormField label="Status">
            <Select {...register("status")}>
              <option value="active">Ativo</option>
              <option value="paused">Pausado</option>
              <option value="cancelled">Cancelado</option>
            </Select>
          </FormField>

          <FormField label="Turno preferido">
            <Select {...register("preferred_shift")}>
              <option value="">Não definido</option>
              <option value="morning">Manhã</option>
              <option value="afternoon">Tarde</option>
              <option value="evening">Noite</option>
            </Select>
          </FormField>

          <div className="flex gap-2 pt-2">
            <Button type="submit" variant="primary" disabled={isSubmitting} className="flex-1">
              {isSubmitting ? "Salvando..." : "Salvar"}
            </Button>
            <Button type="button" variant="ghost" onClick={() => { reset(); onClose(); }}>
              Cancelar
            </Button>
          </div>
        </form>
      ) : null}
    </Drawer>
  );
}
