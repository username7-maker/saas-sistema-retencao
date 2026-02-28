import type { Member } from "../../types";
import { QuickActions } from "../../components/common/QuickActions";
import { Badge, Drawer } from "../../components/ui2";
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
  if (!member) {
    return null;
  }

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
          <p className="mb-2 text-sm font-semibold text-lovable-ink">Acoes Rapidas</p>
          <QuickActions member={member} />
        </div>
      </div>
    </Drawer>
  );
}
