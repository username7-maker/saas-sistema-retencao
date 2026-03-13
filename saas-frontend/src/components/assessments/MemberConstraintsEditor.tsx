import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Pencil, Save, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import { z } from "zod";

import { assessmentService, type MemberConstraints } from "../../services/assessmentService";
import { Button, FormField, Input, Textarea } from "../ui2";
import { ConstraintsAlert } from "./ConstraintsAlert";
import { invalidateAssessmentQueries } from "./queryUtils";

const schema = z.object({
  medical_conditions: z.string().optional(),
  injuries: z.string().optional(),
  medications: z.string().optional(),
  contraindications: z.string().optional(),
  preferred_training_times: z.string().optional(),
  restriction_details: z.string().optional(),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface Props {
  memberId: string;
  constraints: MemberConstraints | null;
}

function restrictionsToText(restrictions: Record<string, unknown> | undefined): string {
  if (!restrictions) {
    return "";
  }

  return Object.entries(restrictions)
    .map(([key, value]) => {
      const text = String(value ?? "").trim();
      if (!text) {
        return "";
      }
      return key === "detalhes" ? text : `${key}: ${text}`;
    })
    .filter(Boolean)
    .join("\n");
}

function textToRestrictions(text?: string): Record<string, string> {
  const lines = (text ?? "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length === 0) {
    return {};
  }

  return Object.fromEntries(
    lines.map((line, index) => {
      const separatorIndex = line.indexOf(":");
      if (separatorIndex > 0) {
        const key = line.slice(0, separatorIndex).trim().toLowerCase().replace(/\s+/g, "_");
        const value = line.slice(separatorIndex + 1).trim();
        return [key || `item_${index + 1}`, value];
      }
      return [index === 0 ? "detalhes" : `item_${index + 1}`, line];
    }),
  );
}

function buildDefaultValues(constraints: MemberConstraints | null): FormValues {
  return {
    medical_conditions: constraints?.medical_conditions ?? "",
    injuries: constraints?.injuries ?? "",
    medications: constraints?.medications ?? "",
    contraindications: constraints?.contraindications ?? "",
    preferred_training_times: constraints?.preferred_training_times ?? "",
    restriction_details: restrictionsToText(constraints?.restrictions),
    notes: constraints?.notes ?? "",
  };
}

export function MemberConstraintsEditor({ memberId, constraints }: Props) {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(!constraints);
  const defaultValues = useMemo(() => buildDefaultValues(constraints), [constraints]);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues,
  });

  useEffect(() => {
    reset(defaultValues);
    if (!constraints) {
      setIsEditing(true);
    }
  }, [constraints, defaultValues, reset]);

  const saveMutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const payload = {
        medical_conditions: values.medical_conditions?.trim() || undefined,
        injuries: values.injuries?.trim() || undefined,
        medications: values.medications?.trim() || undefined,
        contraindications: values.contraindications?.trim() || undefined,
        preferred_training_times: values.preferred_training_times?.trim() || undefined,
        restrictions: textToRestrictions(values.restriction_details),
        notes: values.notes?.trim() || undefined,
      };
      return assessmentService.upsertConstraints(memberId, payload);
    },
    onSuccess: async () => {
      await invalidateAssessmentQueries(queryClient, memberId);
      toast.success("Restricoes salvas.");
      setIsEditing(false);
    },
    onError: () => toast.error("Nao foi possivel salvar as restricoes."),
  });

  if (!isEditing) {
    return (
      <div className="space-y-3">
        <ConstraintsAlert constraints={constraints} />
        <div className="flex justify-end">
          <Button size="sm" variant="secondary" onClick={() => setIsEditing(true)}>
            <Pencil size={14} />
            Editar restricoes
          </Button>
        </div>
      </div>
    );
  }

  return (
    <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Restricoes</h3>
          <p className="mt-1 text-xs text-lovable-ink-muted">Salve aqui o que deve aparecer na aba Restricoes do Perfil 360.</p>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              reset(defaultValues);
              setIsEditing(Boolean(constraints));
            }}
            disabled={saveMutation.isPending}
          >
            <X size={14} />
            Cancelar
          </Button>
          <Button size="sm" variant="primary" onClick={handleSubmit((values) => saveMutation.mutate(values))} disabled={saveMutation.isPending || !isDirty}>
            <Save size={14} />
            {saveMutation.isPending ? "Salvando..." : "Salvar"}
          </Button>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <FormField label="Condicoes de saude" error={errors.medical_conditions?.message}>
          <Textarea rows={3} {...register("medical_conditions")} placeholder="Ex: hipertensao controlada, asma leve..." />
        </FormField>
        <FormField label="Lesoes" error={errors.injuries?.message}>
          <Textarea rows={3} {...register("injuries")} placeholder="Ex: dor lombar, joelho direito..." />
        </FormField>
        <FormField label="Medicacoes" error={errors.medications?.message}>
          <Textarea rows={3} {...register("medications")} placeholder="Ex: anti-inflamatorio eventual, suplementos..." />
        </FormField>
        <FormField label="Contraindicacoes" error={errors.contraindications?.message}>
          <Textarea rows={3} {...register("contraindications")} placeholder="Ex: evitar impacto, evitar agacho profundo..." />
        </FormField>
        <FormField label="Horario preferencial" error={errors.preferred_training_times?.message}>
          <Input {...register("preferred_training_times")} placeholder="Ex: manha, almoco, noite" />
        </FormField>
        <FormField label="Observacoes da equipe" error={errors.notes?.message}>
          <Textarea rows={3} {...register("notes")} placeholder="Contexto clinico e pontos de atencao." />
        </FormField>
      </div>

      <div className="mt-3">
        <FormField label="Restricoes especificas" error={errors.restriction_details?.message}>
          <Textarea
            rows={4}
            {...register("restriction_details")}
            placeholder={"Uma por linha.\nEx: coluna: evitar compressao axial\nombro: nao elevar acima de 90 graus"}
          />
        </FormField>
      </div>
    </section>
  );
}
