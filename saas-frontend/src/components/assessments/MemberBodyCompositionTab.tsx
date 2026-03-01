import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ImageUp, ScanText } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import { z } from "zod";

import { bodyCompositionService } from "../../services/bodyCompositionService";
import { extractBodyCompositionFromText, type BodyCompositionOcrResult } from "../../services/bodyCompositionOcr";
import type { BodyCompositionEvaluationCreate } from "../../types";
import { Button } from "../ui2/Button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui2/Card";
import { FormField } from "../ui2/FormField";
import { Input } from "../ui2/Input";
import { Skeleton } from "../ui2/Skeleton";
import { Textarea } from "../ui2/Textarea";

const schema = z.object({
  evaluation_date: z.string().min(1, "Data obrigatoria"),
  weight_kg: z.preprocess((v) => (v === "" || v == null ? null : Number(v)), z.number().positive().nullable().optional()),
  body_fat_percent: z.preprocess((v) => (v === "" || v == null ? null : Number(v)), z.number().min(0).max(100).nullable().optional()),
  lean_mass_kg: z.preprocess((v) => (v === "" || v == null ? null : Number(v)), z.number().positive().nullable().optional()),
  muscle_mass_kg: z.preprocess((v) => (v === "" || v == null ? null : Number(v)), z.number().positive().nullable().optional()),
  body_water_percent: z.preprocess((v) => (v === "" || v == null ? null : Number(v)), z.number().min(0).max(100).nullable().optional()),
  visceral_fat_level: z.preprocess((v) => (v === "" || v == null ? null : Number(v)), z.number().min(0).nullable().optional()),
  bmi: z.preprocess((v) => (v === "" || v == null ? null : Number(v)), z.number().positive().nullable().optional()),
  basal_metabolic_rate_kcal: z.preprocess((v) => (v === "" || v == null ? null : Number(v)), z.number().positive().nullable().optional()),
  notes: z.string().optional().nullable(),
});

type FormData = z.infer<typeof schema>;

interface Props {
  memberId: string;
}

function fmt(value: number | null | undefined, unit = ""): string {
  if (value == null) return "-";
  return `${value}${unit}`;
}

function fmtDate(dateStr: string): string {
  try {
    return new Date(`${dateStr}T12:00:00`).toLocaleDateString("pt-BR");
  } catch {
    return dateStr;
  }
}

async function readImageWithOcr(file: File): Promise<string> {
  const { createWorker } = await import("tesseract.js");
  const worker = await createWorker("por+eng");
  try {
    const result = await worker.recognize(file);
    return result.data.text ?? "";
  } finally {
    await worker.terminate();
  }
}

export function MemberBodyCompositionTab({ memberId }: Props) {
  const queryClient = useQueryClient();
  const [ocrFile, setOcrFile] = useState<File | null>(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrResult, setOcrResult] = useState<BodyCompositionOcrResult | null>(null);

  const { data: evaluations, isLoading } = useQuery({
    queryKey: ["body-composition", memberId],
    queryFn: () => bodyCompositionService.list(memberId),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  const mutation = useMutation({
    mutationFn: (payload: BodyCompositionEvaluationCreate) => bodyCompositionService.create(memberId, payload),
    onSuccess: () => {
      toast.success("Avaliacao registrada com sucesso.");
      void queryClient.invalidateQueries({ queryKey: ["body-composition", memberId] });
      reset();
      setOcrFile(null);
      setOcrResult(null);
    },
    onError: () => toast.error("Erro ao registrar avaliacao."),
  });

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    getValues,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      evaluation_date: new Date().toISOString().split("T")[0],
    },
  });

  function onSubmit(data: FormData) {
    mutation.mutate({
      ...data,
      source: "tezewa",
    });
  }

  async function handleReadPhoto() {
    if (!ocrFile) {
      toast.error("Selecione uma imagem da bioimpedancia.");
      return;
    }

    setOcrLoading(true);
    try {
      const rawText = await readImageWithOcr(ocrFile);
      const extracted = extractBodyCompositionFromText(rawText);
      setOcrResult(extracted);

      if (extracted.values.evaluation_date) {
        setValue("evaluation_date", extracted.values.evaluation_date);
      } else {
        setValue("evaluation_date", new Date().toISOString().split("T")[0]);
      }

      const numericFields: Array<keyof Pick<FormData,
      "weight_kg" |
      "body_fat_percent" |
      "lean_mass_kg" |
      "muscle_mass_kg" |
      "body_water_percent" |
      "visceral_fat_level" |
      "bmi" |
      "basal_metabolic_rate_kcal">> = [
        "weight_kg",
        "body_fat_percent",
        "lean_mass_kg",
        "muscle_mass_kg",
        "body_water_percent",
        "visceral_fat_level",
        "bmi",
        "basal_metabolic_rate_kcal",
      ];

      let filledCount = 0;
      for (const key of numericFields) {
        const value = extracted.values[key];
        if (typeof value === "number") {
          setValue(key, value);
          filledCount += 1;
        }
      }
      if (extracted.values.evaluation_date) {
        filledCount += 1;
      }

      if (extracted.warnings.length > 0) {
        const currentNotes = getValues("notes") || "";
        const warningText = extracted.warnings.join(" ");
        setValue("notes", [currentNotes, warningText].filter(Boolean).join("\n"));
      }

      toast.success(`Leitura concluida: ${filledCount} campo(s) preenchido(s).`);
    } catch {
      toast.error("Falha ao ler a imagem. Revise os campos manualmente.");
    } finally {
      setOcrLoading(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Registrar Avaliacao de Bioimpedancia</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <section className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">
                Leitura por foto (MVP)
              </p>
              <p className="mt-1 text-xs text-lovable-ink-muted">
                Envie a foto do relatorio Tezewa. O sistema tenta preencher os campos automaticamente e voce revisa antes de salvar.
              </p>
              <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                <Input
                  type="file"
                  accept="image/*"
                  onChange={(event) => setOcrFile(event.target.files?.[0] ?? null)}
                />
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => void handleReadPhoto()}
                  disabled={!ocrFile || ocrLoading}
                >
                  <ScanText size={14} />
                  {ocrLoading ? "Lendo..." : "Ler foto"}
                </Button>
              </div>

              {ocrResult ? (
                <div className="mt-3 space-y-2">
                  <div className="rounded-lg border border-lovable-border bg-lovable-surface p-2 text-xs text-lovable-ink-muted">
                    <p>
                      Confianca estimada: <strong>{Math.round(ocrResult.confidence * 100)}%</strong>
                    </p>
                    {ocrResult.warnings.map((warning, index) => (
                      <p key={index}>- {warning}</p>
                    ))}
                  </div>
                  <details className="rounded-lg border border-lovable-border bg-lovable-surface p-2 text-xs text-lovable-ink-muted">
                    <summary className="cursor-pointer font-semibold">Texto reconhecido da imagem</summary>
                    <pre className="mt-2 max-h-44 overflow-auto whitespace-pre-wrap">{ocrResult.raw_text || "(vazio)"}</pre>
                  </details>
                </div>
              ) : null}
            </section>

            <FormField label="Data da Avaliacao" error={errors.evaluation_date?.message} required>
              <Input type="date" {...register("evaluation_date")} />
            </FormField>

            <div className="grid grid-cols-2 gap-3">
              <FormField label="Peso (kg)" error={errors.weight_kg?.message}>
                <Input type="number" step="0.1" placeholder="Ex: 72.5" {...register("weight_kg")} />
              </FormField>
              <FormField label="% Gordura" error={errors.body_fat_percent?.message}>
                <Input type="number" step="0.1" placeholder="Ex: 18.5" {...register("body_fat_percent")} />
              </FormField>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <FormField label="Massa Magra (kg)" error={errors.lean_mass_kg?.message}>
                <Input type="number" step="0.1" placeholder="Ex: 59.2" {...register("lean_mass_kg")} />
              </FormField>
              <FormField label="Massa Muscular (kg)" error={errors.muscle_mass_kg?.message}>
                <Input type="number" step="0.1" placeholder="Ex: 56.1" {...register("muscle_mass_kg")} />
              </FormField>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <FormField label="% Agua Corporal" error={errors.body_water_percent?.message}>
                <Input type="number" step="0.1" placeholder="Ex: 55.0" {...register("body_water_percent")} />
              </FormField>
              <FormField label="Gordura Visceral (nivel)" error={errors.visceral_fat_level?.message}>
                <Input type="number" step="0.5" placeholder="Ex: 8.5" {...register("visceral_fat_level")} />
              </FormField>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <FormField label="IMC" error={errors.bmi?.message}>
                <Input type="number" step="0.01" placeholder="Ex: 24.3" {...register("bmi")} />
              </FormField>
              <FormField label="TMB (kcal)" error={errors.basal_metabolic_rate_kcal?.message}>
                <Input type="number" step="1" placeholder="Ex: 1650" {...register("basal_metabolic_rate_kcal")} />
              </FormField>
            </div>

            <FormField label="Observacoes" error={errors.notes?.message}>
              <Textarea rows={3} placeholder="Notas adicionais sobre a avaliacao..." {...register("notes")} />
            </FormField>

            <Button type="submit" variant="primary" size="md" className="w-full" disabled={mutation.isPending}>
              <ImageUp size={14} />
              {mutation.isPending ? "Salvando..." : "Salvar Avaliacao"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="flex flex-col gap-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">
          Historico de Avaliacoes
        </h3>

        {isLoading && (
          <div className="space-y-3">
            <Skeleton className="h-32 w-full rounded-2xl" />
            <Skeleton className="h-32 w-full rounded-2xl" />
          </div>
        )}

        {!isLoading && (!evaluations || evaluations.length === 0) && (
          <Card>
            <CardContent className="py-8 text-center">
              <p className="text-sm text-lovable-ink-muted">Nenhuma avaliacao registrada ainda.</p>
            </CardContent>
          </Card>
        )}

        {!isLoading &&
          evaluations?.map((ev) => (
            <Card key={ev.id}>
              <CardContent className="pt-4">
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-sm font-semibold text-lovable-ink">{fmtDate(ev.evaluation_date)}</span>
                  <span className="rounded-full bg-lovable-primary-soft px-2 py-0.5 text-xs font-semibold uppercase tracking-wider text-lovable-primary">
                    {ev.source === "tezewa" ? "Tezewa" : "Manual"}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm sm:grid-cols-3">
                  <Metric label="Peso" value={fmt(ev.weight_kg, " kg")} />
                  <Metric label="% Gordura" value={fmt(ev.body_fat_percent, "%")} />
                  <Metric label="Massa Magra" value={fmt(ev.lean_mass_kg, " kg")} />
                  <Metric label="Massa Musc." value={fmt(ev.muscle_mass_kg, " kg")} />
                  <Metric label="% Agua" value={fmt(ev.body_water_percent, "%")} />
                  <Metric label="Gordura Visc." value={fmt(ev.visceral_fat_level)} />
                  <Metric label="IMC" value={fmt(ev.bmi)} />
                  <Metric label="TMB" value={fmt(ev.basal_metabolic_rate_kcal, " kcal")} />
                </div>

                {ev.notes && (
                  <p className="mt-3 rounded-lg bg-lovable-surface-soft px-3 py-2 text-xs text-lovable-ink-muted">
                    {ev.notes}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-xs text-lovable-ink-muted">{label}</span>
      <p className="font-semibold text-lovable-ink">{value}</p>
    </div>
  );
}
