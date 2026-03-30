import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";

import { Badge, Button, Dialog, Input, Select } from "../../components/ui2";
import { memberService, type MemberBulkUpdatePayload, type MemberBulkUpdatePreviewResult } from "../../services/memberService";
import type { Member } from "../../types";
import type { MemberQueryFilters } from "./memberUtils";

interface BulkUpdateMembersDialogProps {
  open: boolean;
  onClose: () => void;
  selectedMemberIds: string[];
  filteredTotal: number;
  filters: MemberQueryFilters;
  onApplied: () => void;
}

const STATUS_LABELS: Record<Member["status"], string> = {
  active: "Ativo",
  paused: "Pausado",
  cancelled: "Cancelado",
};

const FIELD_LABELS: Record<string, string> = {
  status: "Status",
  plan_name: "Plano",
  monthly_fee: "Mensalidade",
  preferred_shift: "Turno preferido",
};

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatPreviewValue(field: string, value: unknown): string {
  if (value === null || value === undefined || value === "") return "Nao informado";
  if (field === "monthly_fee" && typeof value === "number") return formatCurrency(value);
  if (field === "status" && typeof value === "string") return STATUS_LABELS[value as Member["status"]] ?? value;
  return String(value);
}

export function BulkUpdateMembersDialog({
  open,
  onClose,
  selectedMemberIds,
  filteredTotal,
  filters,
  onApplied,
}: BulkUpdateMembersDialogProps) {
  const queryClient = useQueryClient();
  const [targetMode, setTargetMode] = useState<"selected" | "filtered">(selectedMemberIds.length ? "selected" : "filtered");
  const [applyStatus, setApplyStatus] = useState(false);
  const [applyPlan, setApplyPlan] = useState(false);
  const [applyMonthlyFee, setApplyMonthlyFee] = useState(false);
  const [applyPreferredShift, setApplyPreferredShift] = useState(false);
  const [statusValue, setStatusValue] = useState<Member["status"]>("active");
  const [planNameValue, setPlanNameValue] = useState("");
  const [monthlyFeeValue, setMonthlyFeeValue] = useState("");
  const [preferredShiftValue, setPreferredShiftValue] = useState("");
  const [preview, setPreview] = useState<MemberBulkUpdatePreviewResult | null>(null);
  const [previewSignature, setPreviewSignature] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setTargetMode(selectedMemberIds.length ? "selected" : "filtered");
  }, [open, selectedMemberIds.length]);

  useEffect(() => {
    if (targetMode === "selected" && selectedMemberIds.length === 0) {
      setTargetMode("filtered");
    }
  }, [selectedMemberIds.length, targetMode]);

  useEffect(() => {
    if (!open) {
      setApplyStatus(false);
      setApplyPlan(false);
      setApplyMonthlyFee(false);
      setApplyPreferredShift(false);
      setStatusValue("active");
      setPlanNameValue("");
      setMonthlyFeeValue("");
      setPreferredShiftValue("");
      setPreview(null);
      setPreviewSignature(null);
    }
  }, [open]);

  const payload = useMemo<MemberBulkUpdatePayload | null>(() => {
    const changes: MemberBulkUpdatePayload["changes"] = {};
    if (applyStatus) changes.status = statusValue;
    if (applyPlan && planNameValue.trim()) changes.plan_name = planNameValue.trim();
    if (applyMonthlyFee && monthlyFeeValue.trim() !== "" && !Number.isNaN(Number(monthlyFeeValue))) {
      changes.monthly_fee = Number(monthlyFeeValue);
    }
    if (applyPreferredShift && preferredShiftValue.trim()) changes.preferred_shift = preferredShiftValue.trim();

    if (Object.keys(changes).length === 0) return null;

    return {
      target_mode: targetMode,
      selected_member_ids: targetMode === "selected" ? selectedMemberIds : [],
      filters,
      changes,
    };
  }, [
    applyMonthlyFee,
    applyPlan,
    applyPreferredShift,
    applyStatus,
    filters,
    monthlyFeeValue,
    planNameValue,
    preferredShiftValue,
    selectedMemberIds,
    statusValue,
    targetMode,
  ]);

  const payloadSignature = useMemo(() => JSON.stringify(payload ?? {}), [payload]);
  const previewIsFresh = previewSignature === payloadSignature;

  const previewMutation = useMutation({
    mutationFn: memberService.previewBulkUpdate,
    onSuccess: (data) => {
      setPreview(data);
      setPreviewSignature(payloadSignature);
      toast.success("Preview pronto. Revise antes de aplicar.");
    },
    onError: () => toast.error("Nao foi possivel gerar o preview da atualizacao em massa."),
  });

  const commitMutation = useMutation({
    mutationFn: memberService.bulkUpdate,
    onSuccess: async (result) => {
      toast.success(`${result.updated} membro(s) atualizado(s) com sucesso.`);
      await queryClient.invalidateQueries({ queryKey: ["members"] });
      onApplied();
      onClose();
    },
    onError: () => toast.error("Nao foi possivel aplicar a atualizacao em massa."),
  });

  const handlePreview = () => {
    if (!payload) {
      toast.error("Selecione ao menos um campo para atualizar.");
      return;
    }
    previewMutation.mutate(payload);
  };

  const handleCommit = () => {
    if (!payload || !preview || !previewIsFresh) {
      toast.error("Revalide o preview antes de confirmar.");
      return;
    }
    commitMutation.mutate(payload);
  };

  const canUseSelected = selectedMemberIds.length > 0;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Atualizacao em massa de membros"
      description="Aplique mudancas seguras em lote com preview obrigatorio antes do commit."
      size="md"
    >
      <div className="space-y-5">
        <section className="space-y-3">
          <p className="text-sm font-medium text-lovable-ink">Alvo da operacao</p>
          <label className="flex items-start gap-3 rounded-2xl border border-lovable-border bg-lovable-bg-muted/40 p-3 text-sm text-lovable-ink">
            <input
              type="radio"
              name="bulk-target-mode"
              checked={targetMode === "selected"}
              onChange={() => setTargetMode("selected")}
              disabled={!canUseSelected}
              className="mt-1"
            />
            <span>
              <span className="block font-medium">Membros selecionados</span>
              <span className="text-lovable-ink-muted">
                {canUseSelected ? `${selectedMemberIds.length} selecionado(s) nesta sessao.` : "Nenhum membro selecionado no momento."}
              </span>
            </span>
          </label>
          <label className="flex items-start gap-3 rounded-2xl border border-lovable-border bg-lovable-bg-muted/40 p-3 text-sm text-lovable-ink">
            <input
              type="radio"
              name="bulk-target-mode"
              checked={targetMode === "filtered"}
              onChange={() => setTargetMode("filtered")}
              className="mt-1"
            />
            <span>
              <span className="block font-medium">Todos os membros filtrados</span>
              <span className="text-lovable-ink-muted">{filteredTotal} membro(s) no resultado atual.</span>
            </span>
          </label>
        </section>

        <section className="space-y-4">
          <p className="text-sm font-medium text-lovable-ink">Campos permitidos no bulk update</p>

          <div className="space-y-3 rounded-2xl border border-lovable-border bg-lovable-bg-muted/30 p-4">
            <label className="flex items-center gap-3 text-sm text-lovable-ink">
              <input type="checkbox" checked={applyStatus} onChange={(event) => setApplyStatus(event.target.checked)} />
              <span className="font-medium">Alterar status</span>
            </label>
            {applyStatus ? (
              <Select aria-label="Novo status" value={statusValue} onChange={(event) => setStatusValue(event.target.value as Member["status"])}>
                <option value="active">Ativo</option>
                <option value="paused">Pausado</option>
                <option value="cancelled">Cancelado</option>
              </Select>
            ) : null}

            <label className="flex items-center gap-3 text-sm text-lovable-ink">
              <input type="checkbox" checked={applyPlan} onChange={(event) => setApplyPlan(event.target.checked)} />
              <span className="font-medium">Alterar plano</span>
            </label>
            {applyPlan ? <Input aria-label="Novo plano" value={planNameValue} onChange={(event) => setPlanNameValue(event.target.value)} placeholder="Ex.: Plano Premium" /> : null}

            <label className="flex items-center gap-3 text-sm text-lovable-ink">
              <input type="checkbox" checked={applyMonthlyFee} onChange={(event) => setApplyMonthlyFee(event.target.checked)} />
              <span className="font-medium">Alterar mensalidade</span>
            </label>
            {applyMonthlyFee ? (
              <Input
                aria-label="Nova mensalidade"
                type="number"
                min="0"
                step="0.01"
                value={monthlyFeeValue}
                onChange={(event) => setMonthlyFeeValue(event.target.value)}
                placeholder="0,00"
              />
            ) : null}

            <label className="flex items-center gap-3 text-sm text-lovable-ink">
              <input type="checkbox" checked={applyPreferredShift} onChange={(event) => setApplyPreferredShift(event.target.checked)} />
              <span className="font-medium">Alterar turno preferido</span>
            </label>
            {applyPreferredShift ? (
              <Input
                aria-label="Novo turno preferido"
                value={preferredShiftValue}
                onChange={(event) => setPreferredShiftValue(event.target.value)}
                placeholder="Ex.: manha, tarde, noite"
              />
            ) : null}
          </div>
        </section>

        <section className="space-y-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft/60 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-lovable-ink">Preview obrigatorio</p>
              <p className="text-xs text-lovable-ink-muted">
                Sempre revalide depois de trocar o alvo ou qualquer campo.
              </p>
            </div>
            <Button variant="secondary" onClick={handlePreview} disabled={!payload || previewMutation.isPending}>
              {previewMutation.isPending ? "Gerando preview..." : "Gerar preview"}
            </Button>
          </div>

          {preview ? (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Badge variant="neutral" size="sm">
                  {preview.target_description}
                </Badge>
                <Badge variant="success" size="sm">
                  {preview.would_update} com alteracao
                </Badge>
                <Badge variant="warning" size="sm">
                  {preview.unchanged} sem efeito
                </Badge>
              </div>

              {!previewIsFresh ? (
                <p className="text-xs text-amber-300">
                  O formulario mudou depois do ultimo preview. Gere o preview novamente para confirmar.
                </p>
              ) : null}

              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">
                  Campos alterados
                </p>
                <div className="flex flex-wrap gap-2">
                  {preview.changed_fields.map((field) => (
                    <Badge key={field} variant="neutral" size="sm">
                      {FIELD_LABELS[field] ?? field}
                    </Badge>
                  ))}
                </div>
              </div>

              {preview.sample_members.length ? (
                <div className="space-y-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">
                    Amostra do impacto
                  </p>
                  <div className="space-y-2">
                    {preview.sample_members.map((member) => (
                      <div key={member.id} className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/30 p-3">
                        <p className="font-medium text-lovable-ink">{member.full_name}</p>
                        <p className="text-xs text-lovable-ink-muted">{member.email ?? "Sem email"}</p>
                        <div className="mt-2 space-y-1 text-xs text-lovable-ink-muted">
                          {preview.changed_fields.map((field) => (
                            <p key={`${member.id}-${field}`}>
                              <span className="font-medium text-lovable-ink">{FIELD_LABELS[field] ?? field}:</span>{" "}
                              {formatPreviewValue(field, member.current_values[field])} {" -> "} {formatPreviewValue(field, member.next_values[field])}
                            </p>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-lovable-ink-muted">
                  Nenhum membro teria mudanca efetiva com os valores informados.
                </p>
              )}
            </div>
          ) : (
            <p className="text-sm text-lovable-ink-muted">
              Escolha os campos, gere o preview e confirme so depois de revisar a amostra.
            </p>
          )}
        </section>

        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            variant="primary"
            onClick={handleCommit}
            disabled={!payload || !preview || !previewIsFresh || preview.would_update === 0 || commitMutation.isPending}
          >
            {commitMutation.isPending ? "Aplicando..." : "Confirmar atualizacao"}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
