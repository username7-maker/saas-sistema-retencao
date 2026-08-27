import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { Activity, Ruler, Scale } from "lucide-react";
import toast from "react-hot-toast";

import { invalidateAssessmentQueries } from "./queryUtils";
import { BODY_COMPOSITION_PROTOCOLS } from "./bodyCompositionProtocols";
import { Button, Card, CardContent, FormField, Input, Select, Textarea } from "../ui2";
import {
  assessmentService,
  type AnthropometryAssessmentInput,
  type AnthropometryPreview,
  type AnthropometryProtocol,
} from "../../services/assessmentService";
import { parseLocalizedNumber } from "../../utils/localizedNumber";

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
  neck_cm: "Pescoco",
  shoulders_cm: "Ombros",
  chest_cm: "Torax",
  right_arm_relaxed_cm: "Braco direito relaxado",
  left_arm_relaxed_cm: "Braco esquerdo relaxado",
  right_arm_flexed_cm: "Braco direito contraido",
  left_arm_flexed_cm: "Braco esquerdo contraido",
  right_thigh_cm: "Coxa direita",
  left_thigh_cm: "Coxa esquerda",
  right_calf_cm: "Panturrilha direita",
  left_calf_cm: "Panturrilha esquerda",
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
const LEE_REQUIRED_FIELDS = [
  "right_arm_relaxed_cm",
  "right_thigh_cm",
  "right_calf_cm",
  "skinfold_triceps_mm",
  "skinfold_thigh_mm",
  "skinfold_calf_mm",
] as const;
const FIELD_LIMITS: Record<string, { min: number; max: number; unit: string }> = {
  height_cm: { min: 80, max: 250, unit: "cm" },
  weight_kg: { min: 15, max: 400, unit: "kg" },
};
const EVOLUTION_PERIMETRY_FIELDS = [
  { key: "waist_cm", label: "Cintura (cm)", placeholder: "80.0" },
  { key: "hip_cm", label: "Quadril (cm)", placeholder: "96.0" },
  { key: "shoulders_cm", label: "Ombros (cm)", placeholder: "112.0" },
  { key: "chest_cm", label: "Torax (cm)", placeholder: "98.0" },
  { key: "right_arm_relaxed_cm", label: "Braco direito relaxado (cm)", placeholder: "32.0" },
  { key: "left_arm_relaxed_cm", label: "Braco esquerdo relaxado (cm)", placeholder: "31.8" },
  { key: "right_arm_flexed_cm", label: "Braco direito contraido (cm)", placeholder: "35.0" },
  { key: "left_arm_flexed_cm", label: "Braco esquerdo contraido (cm)", placeholder: "34.8" },
  { key: "right_thigh_cm", label: "Coxa direita (cm)", placeholder: "58.0" },
  { key: "left_thigh_cm", label: "Coxa esquerda (cm)", placeholder: "57.5" },
  { key: "right_calf_cm", label: "Panturrilha direita (cm)", placeholder: "38.0" },
  { key: "left_calf_cm", label: "Panturrilha esquerda (cm)", placeholder: "37.8" },
] as const;

const FALLBACK_ANTHROPOMETRY_PROTOCOLS: AnthropometryProtocol[] = BODY_COMPOSITION_PROTOCOLS
  .filter((protocol) => protocol.supported)
  .map((protocol) => ({
    key: protocol.key,
    label: protocol.label,
    sex: protocol.sex,
    age_min: protocol.ageMin,
    age_max: protocol.ageMax,
    required_fields: protocol.requiredFields,
    required_choice_fields: protocol.requiredChoiceFields ?? [],
    supported: protocol.supported,
    notes: protocol.notes ?? null,
  }));

class AnthropometryClientValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AnthropometryClientValidationError";
  }
}

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
  return parseLocalizedNumber(value);
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
  if (field.startsWith("left_")) return "left";
  return "right";
}

function buildDuplicateMeasurement(value: number, field: string) {
  return {
    attempts: [value, value],
    unit: unitForField(field),
    side: sideForField(field),
  };
}

function limitsForField(field: string): { min: number; max: number; unit: string } {
  if (FIELD_LIMITS[field]) return FIELD_LIMITS[field];
  if (field.endsWith("_mm")) return { min: 1, max: 80, unit: "mm" };
  return { min: 10, max: 300, unit: "cm" };
}

function fieldLabel(field: string): string {
  return FIELD_LABELS[field] ?? field.replace(/_/g, " ");
}

function validateAnthropometryPayload(payload: AnthropometryAssessmentInput): string | null {
  for (const [field, measurement] of Object.entries(payload.measurements)) {
    const limits = limitsForField(field);
    for (const attempt of measurement.attempts) {
      if (!Number.isFinite(attempt)) {
        return `${fieldLabel(field)} tem valor invalido.`;
      }
      if (attempt < limits.min || attempt > limits.max) {
        return `${fieldLabel(field)} precisa estar entre ${limits.min.toFixed(1)} e ${limits.max.toFixed(1)} ${limits.unit}. Confira o valor digitado.`;
      }
    }
  }
  return null;
}

function anthropometryErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof AnthropometryClientValidationError) {
    return error.message;
  }
  if (error instanceof AxiosError) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (detail && typeof detail === "object") {
      const payload = detail as Record<string, unknown>;
      const code = String(payload.code ?? "");
      const field = typeof payload.field === "string" ? payload.field : "";
      const label = field ? fieldLabel(field) : "Medida";
      if (code === "implausible_measurement") {
        const min = payload.minimum != null ? String(payload.minimum).replace(".", ",") : null;
        const max = payload.maximum != null ? String(payload.maximum).replace(".", ",") : null;
        if (min && max) return `${label} fora do intervalo permitido (${min} a ${max}). Confira o valor digitado.`;
        return `${label} fora do intervalo permitido. Confira o valor digitado.`;
      }
      if (code === "third_attempt_required") {
        return `${label}: a diferenca entre as tentativas passou da tolerancia. Preencha a 3a tentativa.`;
      }
      if (code === "measurement_attempt_count_invalid") {
        return `${label}: informe duas tentativas ou a terceira quando necessario.`;
      }
      if (code === "measurement_unit_invalid") {
        return `${label}: unidade invalida para esta medida.`;
      }
      if (code === "side_exception_reason_required") {
        return `${label}: informe o motivo para medir fora do lado padrao.`;
      }
      if (code === "anthropometry_missing_required_measurement") {
        return `${label}: medida obrigatoria ausente.`;
      }
      if (code === "anthropometry_choice_invalid") {
        return `${label}: selecione uma opcao valida para a formula.`;
      }
      if (code === "lee_corrected_circumference_invalid" || code === "lee_muscle_mass_invalid") {
        return "As medidas informadas nao permitem calcular uma massa muscular valida por Lee. Confira perimetros e dobras.";
      }
    }
  }
  return fallback;
}

function anthropometryActuarToast(assessment: { extra_data?: Record<string, unknown> | null }): string {
  const syncState = assessment.extra_data?.actuar_sync;
  if (!syncState || typeof syncState !== "object") return "Avaliacao antropometrica salva.";
  const status = String((syncState as Record<string, unknown>).sync_status ?? "");
  if (status === "sync_pending" || status === "syncing") {
    return "Avaliacao antropometrica salva e enviada ao Actuar.";
  }
  if (status === "saved") {
    return "Avaliacao antropometrica salva. Actuar ficou local/desabilitado neste momento.";
  }
  return "Avaliacao antropometrica salva.";
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
  const [anthropometryEthnicity, setAnthropometryEthnicity] = useState<"white" | "black" | "asian" | "">("");
  const [anthropometryMaturity, setAnthropometryMaturity] = useState<"prepubertal" | "pubertal" | "postpubertal" | "">("");
  const [calculateMuscleMass, setCalculateMuscleMass] = useState(false);
  const [attempts, setAttempts] = useState<Record<string, { first: string; second: string; third?: string }>>({});
  const [perimetry, setPerimetry] = useState<Record<string, string>>({});
  const [observations, setObservations] = useState("");
  const [preview, setPreview] = useState<AnthropometryPreview | null>(null);

  const protocolsQuery = useQuery({
    queryKey: ["anthropometry-protocols"],
    queryFn: () => assessmentService.anthropometryProtocols(),
  });

  const protocolOptions = useMemo(() => {
    return protocolsQuery.data?.length ? protocolsQuery.data : FALLBACK_ANTHROPOMETRY_PROTOCOLS;
  }, [protocolsQuery.data]);

  useEffect(() => {
    const currentProtocolStillExists = protocolOptions.some((protocol) => protocol.key === protocolKey);
    if (protocolOptions.length && (!protocolKey || !currentProtocolStillExists)) {
      const preferred = protocolOptions.find((protocol) => protocol.sex === sex) ?? protocolOptions[0];
      setProtocolKey(preferred.key);
    }
  }, [protocolKey, protocolOptions, sex]);

  const selectedProtocol = useMemo<AnthropometryProtocol | null>(() => {
    return protocolOptions.find((protocol) => protocol.key === protocolKey) ?? null;
  }, [protocolKey, protocolOptions]);

  const dynamicFields = useMemo(() => {
    const fields = new Set<string>(selectedProtocol?.required_fields ?? []);
    if (calculateMuscleMass) {
      LEE_REQUIRED_FIELDS.forEach((field) => fields.add(field));
    }
    return Array.from(fields).filter((field) => !SKIP_DYNAMIC_FIELDS.has(field));
  }, [calculateMuscleMass, selectedProtocol]);

  const requiresSlaughterEthnicity = selectedProtocol?.required_choice_fields?.includes("anthropometry_ethnicity") ?? false;
  const requiresMaturity = selectedProtocol?.required_choice_fields?.includes("anthropometry_maturity") ?? false;
  const requiresEthnicity = requiresSlaughterEthnicity || calculateMuscleMass;

  useEffect(() => {
    if (requiresSlaughterEthnicity && anthropometryEthnicity === "asian") {
      setAnthropometryEthnicity("");
    }
  }, [anthropometryEthnicity, requiresSlaughterEthnicity]);

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

  function updatePerimetry(field: string, value: string) {
    setPerimetry((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function openPdfPopupSafely(): Window | null {
    if (navigator.userAgent.toLowerCase().includes("jsdom")) return null;
    try {
      return window.open("", "_blank");
    } catch {
      return null;
    }
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

    for (const item of EVOLUTION_PERIMETRY_FIELDS) {
      if (measurements[item.key]) continue;
      const value = toNumber(perimetry[item.key] ?? "");
      if (value != null) {
        measurements[item.key] = buildDuplicateMeasurement(value, item.key);
      }
    }

    return {
      assessment_date: assessmentDate ? new Date(assessmentDate).toISOString() : undefined,
      sex_for_formula: sex,
      age_years: toNumber(ageYears),
      measurement_protocol: protocolKey,
      anthropometry_ethnicity: anthropometryEthnicity || null,
      anthropometry_maturity: anthropometryMaturity || null,
      calculate_muscle_mass: calculateMuscleMass,
      measurements,
      observations: observations || undefined,
    };
  }

  function buildValidatedPayload(): AnthropometryAssessmentInput {
    const payload = buildPayload();
    if (payload.age_years == null || payload.age_years <= 0) {
      throw new AnthropometryClientValidationError("Informe uma idade valida para calcular TMB e composicao corporal.");
    }
    if (requiresSlaughterEthnicity && !payload.anthropometry_ethnicity) {
      throw new AnthropometryClientValidationError("Selecione o grupo etnico usado no protocolo Slaughter.");
    }
    if (requiresMaturity && !payload.anthropometry_maturity) {
      throw new AnthropometryClientValidationError("Selecione o estagio maturacional usado no protocolo Slaughter.");
    }
    if (calculateMuscleMass && !payload.anthropometry_ethnicity) {
      throw new AnthropometryClientValidationError("Selecione o grupo etnico usado no calculo de massa muscular.");
    }
    const validationError = validateAnthropometryPayload(payload);
    if (validationError) throw new AnthropometryClientValidationError(validationError);
    return payload;
  }

  const previewMutation = useMutation({
    mutationFn: (payload: AnthropometryAssessmentInput) => assessmentService.previewAnthropometry(memberId, payload),
    onSuccess: (result) => setPreview(result),
    onError: (error) => toast.error(anthropometryErrorMessage(error, "Nao foi possivel calcular a previa antropometrica.")),
  });

  const createMutation = useMutation({
    mutationFn: ({ payload, popup }: { payload: AnthropometryAssessmentInput; popup: Window | null }) =>
      assessmentService.createAnthropometry(memberId, payload, idempotencyKey).then((assessment) => ({ assessment, popup })),
    onSuccess: async ({ assessment, popup }) => {
      await invalidateAssessmentQueries(queryClient, memberId);
      try {
        await assessmentService.openAnthropometryPdf(memberId, assessment.id, popup);
      } catch {
        popup?.close();
        toast.error("A avaliacao foi salva, mas nao foi possivel gerar o PDF agora.");
      }
      toast.success(anthropometryActuarToast(assessment));
      onSaved?.();
    },
    onError: (_error, variables) => {
      variables?.popup?.close();
      toast.error(anthropometryErrorMessage(_error, "Nao foi possivel salvar a avaliacao antropometrica."));
    },
  });

  function handlePreview() {
    try {
      previewMutation.mutate(buildValidatedPayload());
    } catch (error) {
      toast.error(anthropometryErrorMessage(error, "Nao foi possivel calcular a previa antropometrica."));
    }
  }

  function handleConfirm() {
    try {
      createMutation.mutate({ payload: buildValidatedPayload(), popup: openPdfPopupSafely() });
    } catch (error) {
      toast.error(anthropometryErrorMessage(error, "Nao foi possivel salvar a avaliacao antropometrica."));
    }
  }

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
            Massa muscular pode ser estimada opcionalmente por Lee. Agua corporal, gordura visceral, massa ossea e idade metabolica permanecem indisponiveis.
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
          <FormField label="Idade usada na formula" required>
            <Input aria-label="Idade usada na formula" type="text" inputMode="numeric" value={ageYears} onChange={(event) => setAgeYears(event.target.value)} />
          </FormField>
          <FormField label="Altura (cm)">
            <Input aria-label="Altura" type="text" inputMode="decimal" value={height} onChange={(event) => setHeight(event.target.value)} />
          </FormField>
          <FormField label="Peso (kg)" required>
            <Input aria-label="Peso" type="text" inputMode="decimal" value={weight} onChange={(event) => setWeight(event.target.value)} />
          </FormField>
          <FormField label="Protocolo" required>
            <Select aria-label="Protocolo" value={protocolKey} onChange={(event) => setProtocolKey(event.target.value)}>
              {protocolOptions.map((protocol) => (
                <option key={protocol.key} value={protocol.key}>
                  {protocol.label}
                </option>
              ))}
            </Select>
            {protocolsQuery.isError ? (
              <p className="mt-1 text-xs text-yellow-300">Lista carregada pelo catalogo local. A API de protocolos nao respondeu agora.</p>
            ) : null}
          </FormField>
          {requiresEthnicity ? (
            <FormField label={calculateMuscleMass ? "Grupo etnico usado nas formulas" : "Grupo etnico usado na formula"} required>
              <Select
                aria-label="Grupo etnico usado na formula"
                value={anthropometryEthnicity}
                onChange={(event) => setAnthropometryEthnicity(event.target.value as typeof anthropometryEthnicity)}
              >
                <option value="">Selecione</option>
                <option value="white">{requiresSlaughterEthnicity ? "Branco" : "Branco ou hispanico"}</option>
                <option value="black">Negro</option>
                {!requiresSlaughterEthnicity ? <option value="asian">Asiatico</option> : null}
              </Select>
            </FormField>
          ) : null}
          {requiresMaturity ? (
            <FormField label="Estagio maturacional" required>
              <Select
                aria-label="Estagio maturacional"
                value={anthropometryMaturity}
                onChange={(event) => setAnthropometryMaturity(event.target.value as typeof anthropometryMaturity)}
              >
                <option value="">Selecione</option>
                <option value="prepubertal">Pre-pubere</option>
                <option value="pubertal">Pubere</option>
                <option value="postpubertal">Pos-pubere</option>
              </Select>
            </FormField>
          ) : null}
        </div>
      </section>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <label className="flex items-start gap-3">
          <input
            type="checkbox"
            className="mt-1 h-4 w-4 rounded border border-lovable-border"
            checked={calculateMuscleMass}
            onChange={(event) => setCalculateMuscleMass(event.target.checked)}
          />
          <span>
            <span className="block text-sm font-semibold text-lovable-ink">Calcular massa muscular</span>
            <span className="mt-1 block text-xs text-lovable-ink-muted">
              Usa Lee et al. (2000) com braco, coxa e panturrilha direitos corrigidos pelas respectivas dobras.
            </span>
          </span>
        </label>
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
                    type="text"
                    inputMode="decimal"
                    value={attempts[field]?.first ?? ""}
                    onChange={(event) => updateAttempt(field, "first", event.target.value)}
                  />
                  <Input
                    aria-label={`${label} - tentativa 2`}
                    type="text"
                    inputMode="decimal"
                    value={attempts[field]?.second ?? ""}
                    onChange={(event) => updateAttempt(field, "second", event.target.value)}
                  />
                  <Input
                    aria-label={`${label} - tentativa 3`}
                    type="text"
                    inputMode="decimal"
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
        <h3 className="mb-1 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Perimetria para evolucao</h3>
        <p className="mb-3 text-xs text-lovable-ink-muted">
          Medidas usadas para acompanhar evolucao. Elas so entram no calculo de gordura corporal quando o protocolo exigir.
        </p>
        <div className="grid gap-3 md:grid-cols-2">
          {EVOLUTION_PERIMETRY_FIELDS.filter((item) => !dynamicFields.includes(item.key)).map((item) => (
            <FormField key={item.key} label={item.label}>
              <Input
                aria-label={item.label}
                type="text"
                inputMode="decimal"
                placeholder={item.placeholder}
                value={perimetry[item.key] ?? ""}
                onChange={(event) => updatePerimetry(item.key, event.target.value)}
              />
            </FormField>
          ))}
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
            <PreviewMetric label="RCQ" value={preview.results.waist_hip_ratio != null ? String(preview.results.waist_hip_ratio) : "-"} />
            <PreviewMetric label="TMB estimada" value={preview.results.basal_metabolic_rate != null ? `${preview.results.basal_metabolic_rate} kcal/dia` : "-"} />
            {calculateMuscleMass ? (
              <PreviewMetric label="Massa muscular estimada" value={preview.results.muscle_mass_kg != null ? `${preview.results.muscle_mass_kg} kg` : "-"} />
            ) : null}
          </div>
          {!calculateMuscleMass ? <p className="mt-3 text-sm font-medium text-lovable-ink">Massa muscular: calculo opcional nao selecionado</p> : null}
          {Array.isArray(preview.snapshot.flags) && preview.snapshot.flags.some((flag) => String(flag).startsWith("lee_")) ? (
            <p className="mt-3 text-xs font-medium text-yellow-300">
              A estimativa de Lee esta fora da populacao adulta nao obesa usada na validacao original e deve ser interpretada como extrapolacao.
            </p>
          ) : null}
          <p className="mt-1 text-xs text-lovable-ink-muted">Hash do calculo: {preview.calculation_hash}</p>
        </section>
      ) : null}

      <div className="flex flex-wrap items-center justify-end gap-3">
        <Button type="button" variant="secondary" onClick={handlePreview} disabled={previewMutation.isPending || !protocolKey}>
          {previewMutation.isPending ? "Calculando..." : "Calcular previa"}
        </Button>
        <Button
          type="button"
          variant="primary"
          onClick={handleConfirm}
          disabled={createMutation.isPending || !preview}
        >
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
