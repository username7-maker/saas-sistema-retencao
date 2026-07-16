import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, Ruler, Scale } from "lucide-react";
import toast from "react-hot-toast";

import { invalidateAssessmentQueries } from "./queryUtils";
import { Button, Card, CardContent, FormField, Input, Select, Textarea } from "../ui2";
import {
  assessmentService,
  type AnthropometryAssessmentInput,
  type AnthropometryPreview,
  type AnthropometryProtocol,
} from "../../services/assessmentService";

type SexForFormula = "male" | "female";

interface AssessmentComposerMember {
  id?: string;
  full_name?: string;
  birthdate?: string | null;
  sex_for_clinical_calculation?: SexForFormula | null;
  height_cm?: number | null;
}

interface AssessmentRegistrationComposerProps {
  memberId: string;
  member?: AssessmentComposerMember | null;
  initialMode?: "select" | "manual_anthropometry";
  onOpenBioimpedance?: () => void;
  onSaved?: () => void;
}

const FIELD_LABELS: Record<string, string> = {
  height_cm: "Altura",
  weight_kg: "Peso",
  waist_cm: "Cintura",
  hip_cm: "Quadril",
  abdomen_cm: "Abdomen",
  skinfold_chest_mm: "Dobra peitoral",
  skinfold_midaxillary_mm: "Dobra axilar media",
  skinfold_subscapular_mm: "Dobra subescapular",
  skinfold_triceps_mm: "Dobra tricipital",
  skinfold_biceps_mm: "Dobra bicipital",
  skinfold_abdominal_mm: "Dobra abdominal",
  skinfold_suprailiac_mm: "Dobra suprailiaca",
  skinfold_thigh_mm: "Dobra coxa",
  skinfold_calf_mm: "Dobra panturrilha",
};

const SKIP_DYNAMIC_FIELDS = new Set(["height_cm", "weight_kg"]);

function defaultDateTimeLocal(): string {
  const now = new Date();
  const tzOffsetMs = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - tzOffsetMs).toISOString().slice(0, 16);
}

function calculateAge(birthdate?: string | null): number | null {
  if (!birthdate) return null;
  const parsed = new Date(`${birthdate}T12:00:00`);
  if (Number.isNaN(parsed.getTime())) return null;
  const today = new Date();
  let age = today.getFullYear() - parsed.getFullYear();
  const monthDelta = today.getMonth() - parsed.getMonth();
  if (monthDelta < 0 || (monthDelta === 0 && today.getDate() < parsed.getDate())) age -= 1;
  return age;
}

function toNumber(value: string): number | null {
  const normalized = value.replace(",", ".").trim();
  if (!normalized) return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function randomIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (char) => {
    const random = Math.floor(Math.random() * 16);
    const value = char === "x" ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
}

function unitForField(field: string): "mm" | "cm" | "kg" {
  if (field === "weight_kg") return "kg";
  if (field.endsWith("_mm")) return "mm";
  return "cm";
}

function sideForField(field: string): "right" | "left" | "not_applicable" {
  if (field === "height_cm" || field === "weight_kg") return "not_applicable";
  return "right";
}

function buildDuplicateMeasurement(value: number, field: string) {
  return {
    attempts: [value, value],
    unit: unitForField(field),
    side: sideForField(field),
  };
}

export function AssessmentRegistrationComposer({
  memberId,
  member,
  initialMode = "select",
  onOpenBioimpedance,
  onSaved,
}: AssessmentRegistrationComposerProps) {
  const [mode, setMode] = useState<"select" | "manual_anthropometry">(initialMode);
  const [idempotencyKey, setIdempotencyKey] = useState(randomIdempotencyKey);

  useEffect(() => {
    setMode(initialMode);
  }, [initialMode]);

  if (mode === "manual_anthropometry") {
    return (
      <ManualAnthropometricAssessmentForm
        memberId={memberId}
        member={member}
        idempotencyKey={idempotencyKey}
        onSaved={() => {
          setIdempotencyKey(randomIdempotencyKey());
          onSaved?.();
        }}
      />
    );
  }

  return (
    <div className="space-y-4">
      <section className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardContent className="space-y-4 pt-5">
            <div className="flex items-center gap-3">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-lovable-border bg-lovable-surface-soft">
                <Scale size={18} />
              </span>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Modo existente</p>
                <h3 className="font-heading text-lg font-bold text-lovable-ink">Com bioimpedancia</h3>
              </div>
            </div>
            <p className="text-sm text-lovable-ink-muted">
              Abre a aba atual de bioimpedancia para importar ou revisar os dados da balanca.
            </p>
            <Button type="button" variant="primary" onClick={onOpenBioimpedance}>
              Com bioimpedancia
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4 pt-5">
            <div className="flex items-center gap-3">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-lovable-border bg-lovable-surface-soft">
                <Ruler size={18} />
              </span>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Novo modo local</p>
                <h3 className="font-heading text-lg font-bold text-lovable-ink">Sem bioimpedancia</h3>
              </div>
            </div>
            <p className="text-sm text-lovable-ink-muted">
              Usa peso, altura, perimetros e dobras para calcular os indicadores antropometricos possiveis.
            </p>
            <Button type="button" variant="secondary" onClick={() => setMode("manual_anthropometry")}>
              Sem bioimpedancia
            </Button>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function ManualAnthropometricAssessmentForm({
  memberId,
  member,
  idempotencyKey,
  onSaved,
}: {
  memberId: string;
  member?: AssessmentComposerMember | null;
  idempotencyKey: string;
  onSaved?: () => void;
}) {
  const queryClient = useQueryClient();
  const ageFromBirthdate = calculateAge(member?.birthdate);
  const [assessmentDate, setAssessmentDate] = useState(defaultDateTimeLocal);
  const [sex, setSex] = useState<SexForFormula>((member?.sex_for_clinical_calculation ?? "male") as SexForFormula);
  const [ageYears, setAgeYears] = useState(ageFromBirthdate?.toString() ?? "");
  const [height, setHeight] = useState(member?.height_cm != null ? String(member.height_cm) : "");
  const [weight, setWeight] = useState("");
  const [protocolKey, setProtocolKey] = useState("");
  const [attempts, setAttempts] = useState<Record<string, { first: string; second: string; third?: string }>>({});
  const [waist, setWaist] = useState("");
  const [hip, setHip] = useState("");
  const [observations, setObservations] = useState("");
  const [preview, setPreview] = useState<AnthropometryPreview | null>(null);

  const protocolsQuery = useQuery({
    queryKey: ["anthropometry-protocols"],
    queryFn: () => assessmentService.anthropometryProtocols(),
  });

  useEffect(() => {
    if (!protocolKey && protocolsQuery.data?.length) {
      const preferred = protocolsQuery.data.find((protocol) => protocol.sex === sex) ?? protocolsQuery.data[0];
      setProtocolKey(preferred.key);
    }
  }, [protocolKey, protocolsQuery.data, sex]);

  const selectedProtocol = useMemo<AnthropometryProtocol | null>(() => {
    return protocolsQuery.data?.find((protocol) => protocol.key === protocolKey) ?? null;
  }, [protocolKey, protocolsQuery.data]);

  const dynamicFields = useMemo(() => {
    return (selectedProtocol?.required_fields ?? []).filter((field) => !SKIP_DYNAMIC_FIELDS.has(field));
  }, [selectedProtocol]);

  function updateAttempt(field: string, key: "first" | "second" | "third", value: string) {
    setAttempts((current) => ({
      ...current,
      [field]: {
        first: current[field]?.first ?? "",
        second: current[field]?.second ?? "",
        third: current[field]?.third ?? "",
        [key]: value,
      },
    }));
  }

  function buildPayload(): AnthropometryAssessmentInput {
    const measurements: AnthropometryAssessmentInput["measurements"] = {};
    const heightValue = toNumber(height);
    const weightValue = toNumber(weight);
    if (heightValue != null) measurements.height_cm = buildDuplicateMeasurement(heightValue, "height_cm");
    if (weightValue != null) measurements.weight_kg = buildDuplicateMeasurement(weightValue, "weight_kg");

    for (const field of dynamicFields) {
      const fieldAttempts = attempts[field];
      const first = toNumber(fieldAttempts?.first ?? "");
      const second = toNumber(fieldAttempts?.second ?? "");
      const third = toNumber(fieldAttempts?.third ?? "");
      const values = [first, second, third].filter((value): value is number => value != null);
      if (values.length >= 2) {
        measurements[field] = {
          attempts: values,
          unit: unitForField(field),
          side: sideForField(field),
        };
      }
    }

    const waistValue = toNumber(waist);
    const hipValue = toNumber(hip);
    if (waistValue != null) measurements.waist_cm = buildDuplicateMeasurement(waistValue, "waist_cm");
    if (hipValue != null) measurements.hip_cm = buildDuplicateMeasurement(hipValue, "hip_cm");

    return {
      assessment_date: assessmentDate ? new Date(assessmentDate).toISOString() : undefined,
      sex_for_formula: sex,
      age_years: toNumber(ageYears),
      measurement_protocol: protocolKey,
      measurements,
      observations: observations || undefined,
    };
  }

  const previewMutation = useMutation({
    mutationFn: () => assessmentService.previewAnthropometry(memberId, buildPayload()),
    onSuccess: (result) => setPreview(result),
    onError: () => toast.error("Nao foi possivel calcular a previa antropometrica."),
  });

  const createMutation = useMutation({
    mutationFn: () => assessmentService.createAnthropometry(memberId, buildPayload(), idempotencyKey),
    onSuccess: async () => {
      await invalidateAssessmentQueries(queryClient, memberId);
      toast.success("Avaliacao antropometrica salva.");
      onSaved?.();
    },
    onError: () => toast.error("Nao foi possivel salvar a avaliacao antropometrica."),
  });

  return (
    <form className="space-y-4" onSubmit={(event) => event.preventDefault()}>
      <Card>
        <CardContent className="space-y-3 pt-5">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-lovable-border bg-lovable-surface-soft">
              <Activity size={18} />
            </span>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Avaliacao antropometrica</p>
              <h3 className="font-heading text-lg font-bold text-lovable-ink">Sem bioimpedancia</h3>
            </div>
          </div>
          <p className="text-sm text-lovable-ink-muted">
            Massa muscular, agua corporal, gordura visceral, massa ossea e idade metabolica permanecem indisponiveis nesta modalidade.
          </p>
        </CardContent>
      </Card>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Dados da avaliacao</h3>
        <div className="grid gap-3 md:grid-cols-3">
          <FormField label="Data da avaliacao">
            <Input aria-label="Data da avaliacao" type="datetime-local" value={assessmentDate} onChange={(event) => setAssessmentDate(event.target.value)} />
          </FormField>
          <FormField label="Sexo usado na formula">
            <Select aria-label="Sexo usado na formula" value={sex} onChange={(event) => setSex(event.target.value as SexForFormula)}>
              <option value="male">Masculino</option>
              <option value="female">Feminino</option>
            </Select>
          </FormField>
          <FormField label="Idade usada na formula">
            <Input aria-label="Idade usada na formula" type="number" value={ageYears} onChange={(event) => setAgeYears(event.target.value)} />
          </FormField>
          <FormField label="Altura (cm)">
            <Input aria-label="Altura" type="number" step="0.1" value={height} onChange={(event) => setHeight(event.target.value)} />
          </FormField>
          <FormField label="Peso (kg)" required>
            <Input aria-label="Peso" type="number" step="0.1" value={weight} onChange={(event) => setWeight(event.target.value)} />
          </FormField>
          <FormField label="Protocolo" required>
            <Select aria-label="Protocolo" value={protocolKey} onChange={(event) => setProtocolKey(event.target.value)}>
              {(protocolsQuery.data ?? []).map((protocol) => (
                <option key={protocol.key} value={protocol.key}>
                  {protocol.label}
                </option>
              ))}
            </Select>
          </FormField>
        </div>
      </section>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="mb-1 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Dobras e perimetros do protocolo</h3>
        <p className="mb-3 text-xs text-lovable-ink-muted">Complete a primeira rodada de todos os pontos antes da segunda rodada.</p>
        <div className="grid gap-3 md:grid-cols-2">
          {dynamicFields.map((field) => {
            const label = FIELD_LABELS[field] ?? field;
            return (
              <div key={field} className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">{label}</p>
                <div className="grid gap-2 md:grid-cols-3">
                  <Input
                    aria-label={`${label} - tentativa 1`}
                    type="number"
                    step="0.1"
                    value={attempts[field]?.first ?? ""}
                    onChange={(event) => updateAttempt(field, "first", event.target.value)}
                  />
                  <Input
                    aria-label={`${label} - tentativa 2`}
                    type="number"
                    step="0.1"
                    value={attempts[field]?.second ?? ""}
                    onChange={(event) => updateAttempt(field, "second", event.target.value)}
                  />
                  <Input
                    aria-label={`${label} - tentativa 3`}
                    type="number"
                    step="0.1"
                    value={attempts[field]?.third ?? ""}
                    onChange={(event) => updateAttempt(field, "third", event.target.value)}
                    placeholder="3a se necessario"
                  />
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Perimetros opcionais</h3>
        <div className="grid gap-3 md:grid-cols-3">
          <FormField label="Cintura (cm)">
            <Input aria-label="Cintura" type="number" step="0.1" value={waist} onChange={(event) => setWaist(event.target.value)} />
          </FormField>
          <FormField label="Quadril (cm)">
            <Input aria-label="Quadril" type="number" step="0.1" value={hip} onChange={(event) => setHip(event.target.value)} />
          </FormField>
        </div>
      </section>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <FormField label="Observacoes">
          <Textarea
            aria-label="Observacoes"
            rows={3}
            value={observations}
            onChange={(event) => setObservations(event.target.value)}
            placeholder="Notas do professor, condicoes da medida ou contexto do protocolo."
          />
        </FormField>
      </section>

      {preview ? (
        <section className="rounded-2xl border border-lovable-primary/25 bg-lovable-primary-soft p-4 shadow-panel">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-primary">Previa calculada</h3>
          <div className="mt-3 grid gap-3 md:grid-cols-4">
            <PreviewMetric label="Gordura corporal" value={preview.results.body_fat_pct != null ? `${preview.results.body_fat_pct}%` : "-"} />
            <PreviewMetric label="IMC" value={preview.results.bmi != null ? String(preview.results.bmi) : "-"} />
            <PreviewMetric label="Massa de gordura" value={preview.results.fat_mass_kg != null ? `${preview.results.fat_mass_kg} kg` : "-"} />
            <PreviewMetric label="Massa livre" value={preview.results.lean_mass_kg != null ? `${preview.results.lean_mass_kg} kg` : "-"} />
          </div>
          <p className="mt-3 text-sm font-medium text-lovable-ink">Massa muscular: indisponivel nesta modalidade</p>
          <p className="mt-1 text-xs text-lovable-ink-muted">Hash do calculo: {preview.calculation_hash}</p>
        </section>
      ) : null}

      <div className="flex flex-wrap items-center justify-end gap-3">
        <Button type="button" variant="secondary" onClick={() => previewMutation.mutate()} disabled={previewMutation.isPending || !protocolKey}>
          {previewMutation.isPending ? "Calculando..." : "Calcular previa"}
        </Button>
        <Button type="button" variant="primary" onClick={() => createMutation.mutate()} disabled={createMutation.isPending || !preview}>
          {createMutation.isPending ? "Salvando..." : "Confirmar avaliacao"}
        </Button>
      </div>
    </form>
  );
}

function PreviewMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-lovable-border bg-lovable-surface px-3 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold text-lovable-ink">{value}</p>
    </div>
  );
}
