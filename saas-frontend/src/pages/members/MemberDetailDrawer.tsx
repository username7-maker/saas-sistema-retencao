import { useState } from "react";
import toast from "react-hot-toast";
import type { Member } from "../../types";
import { QuickActions } from "../../components/common/QuickActions";
import { Badge, Drawer } from "../../components/ui2";
import { lgpdService } from "../../services/lgpdService";
import { RISK_LABELS, RISK_VARIANTS, STATUS_LABELS, STATUS_VARIANTS } from "./memberUtils";

export function MemberDetailDrawer({
  member,
  open,
  onClose,
}: {
  member: Member | null;
  open: boolean;
  onClose: () => void;
}) {
  const [confirmAnonymize, setConfirmAnonymize] = useState(false);
  const [lgpdLoading, setLgpdLoading] = useState(false);

  if (!member) {
    return null;
  }

  const handleExportLgpd = async () => {
    setLgpdLoading(true);
    try {
      await lgpdService.exportMemberPdf(member.id);
      toast.success("PDF de dados gerado com sucesso");
    } catch {
      toast.error("Erro ao exportar dados LGPD");
    } finally {
      setLgpdLoading(false);
    }
  };

  const handleAnonymize = async () => {
    setLgpdLoading(true);
    try {
      await lgpdService.anonymizeMember(member.id);
      toast.success("Dados do membro anonimizados");
      setConfirmAnonymize(false);
      onClose();
    } catch {
      toast.error("Erro ao anonimizar membro");
    } finally {
      setLgpdLoading(false);
    }
  };

  const lastCheckin = member.last_checkin_at
    ? new Date(member.last_checkin_at).toLocaleDateString("pt-BR")
    : "Nunca";

  return (
    <Drawer open={open} onClose={onClose} title={member.full_name}>
      <div className="space-y-4 p-4">
        <div className="flex items-center gap-3">
          <Badge variant={RISK_VARIANTS[member.risk_level]}>
            Risco {RISK_LABELS[member.risk_level]} ({member.risk_score})
          </Badge>
          <Badge variant={STATUS_VARIANTS[member.status]}>{STATUS_LABELS[member.status]}</Badge>
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-lovable-ink-muted">Email</p>
            <p className="font-medium text-lovable-ink">{member.email ?? "-"}</p>
          </div>
          <div>
            <p className="text-lovable-ink-muted">Telefone</p>
            <p className="font-medium text-lovable-ink">{member.phone ?? "-"}</p>
          </div>
          <div>
            <p className="text-lovable-ink-muted">Plano</p>
            <p className="font-medium text-lovable-ink">{member.plan_name}</p>
          </div>
          <div>
            <p className="text-lovable-ink-muted">Mensalidade</p>
            <p className="font-medium text-lovable-ink">
              {member.monthly_fee.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
            </p>
          </div>
          <div>
            <p className="text-lovable-ink-muted">Membro desde</p>
            <p className="font-medium text-lovable-ink">{new Date(member.join_date).toLocaleDateString("pt-BR")}</p>
          </div>
          <div>
            <p className="text-lovable-ink-muted">Ultimo check-in</p>
            <p className="font-medium text-lovable-ink">{lastCheckin}</p>
          </div>
          <div>
            <p className="text-lovable-ink-muted">Fidelidade</p>
            <p className="font-medium text-lovable-ink">{member.loyalty_months} meses</p>
          </div>
          <div>
            <p className="text-lovable-ink-muted">NPS</p>
            <p className="font-medium text-lovable-ink">{member.nps_last_score > 0 ? member.nps_last_score : "-"}</p>
          </div>
        </div>

        <div className="border-t border-lovable-border pt-3">
          <p className="mb-2 text-sm font-semibold text-lovable-ink">Ações Rápidas</p>
          <QuickActions member={member} />
        </div>

        <div className="border-t border-lovable-border pt-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">LGPD</p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void handleExportLgpd()}
              disabled={lgpdLoading}
              className="rounded-full border border-lovable-border px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted hover:bg-lovable-surface-soft disabled:opacity-50"
            >
              Exportar dados
            </button>
            {!confirmAnonymize ? (
              <button
                type="button"
                onClick={() => setConfirmAnonymize(true)}
                disabled={lgpdLoading}
                className="rounded-full border border-lovable-danger/40 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-lovable-danger hover:bg-lovable-danger/5 disabled:opacity-50"
              >
                Anonimizar
              </button>
            ) : (
              <div className="flex items-center gap-2">
                <p className="text-xs text-lovable-danger">Confirmar anonimização?</p>
                <button
                  type="button"
                  onClick={() => void handleAnonymize()}
                  disabled={lgpdLoading}
                  className="rounded-full bg-lovable-danger px-3 py-1 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50"
                >
                  {lgpdLoading ? "..." : "Confirmar"}
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmAnonymize(false)}
                  className="text-xs text-lovable-ink-muted hover:text-lovable-ink"
                >
                  Cancelar
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </Drawer>
  );
}
