import { useState } from "react";
import { BarChart3, ShieldAlert, Briefcase, Wallet, Activity, FileText, Send } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import toast from "react-hot-toast";

import { reportService, type DashboardReportType } from "../../services/reportService";
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui2";

interface ReportCardConfig {
  type: DashboardReportType;
  title: string;
  description: string;
  icon: LucideIcon;
}

const REPORT_CARDS: ReportCardConfig[] = [
  { type: "executive", title: "Executivo", description: "Visao geral de KPIs", icon: BarChart3 },
  { type: "retention", title: "Retencao", description: "Risco, NPS e alertas", icon: ShieldAlert },
  { type: "commercial", title: "Comercial", description: "Leads e conversao", icon: Briefcase },
  { type: "financial", title: "Financeiro", description: "MRR, LTV e receita", icon: Wallet },
  { type: "operational", title: "Operacional", description: "Check-ins e inatividade", icon: Activity },
  { type: "consolidated", title: "Consolidado", description: "Relatorio completo", icon: FileText },
];

function initialLoadingMap(): Record<DashboardReportType, boolean> {
  return {
    executive: false,
    operational: false,
    commercial: false,
    financial: false,
    retention: false,
    consolidated: false,
  };
}

export default function ReportsPage() {
  const [loadingByType, setLoadingByType] = useState<Record<DashboardReportType, boolean>>(initialLoadingMap);
  const [dispatching, setDispatching] = useState(false);

  const handleDownload = async (type: DashboardReportType) => {
    setLoadingByType((prev) => ({ ...prev, [type]: true }));
    try {
      await reportService.exportDashboardPdf(type);
      toast.success(`Relatorio ${type} gerado com sucesso!`);
    } catch {
      toast.error("Falha ao exportar PDF.");
    } finally {
      setLoadingByType((prev) => ({ ...prev, [type]: false }));
    }
  };

  const handleDispatchMonthly = async () => {
    setDispatching(true);
    try {
      await reportService.dispatchMonthlyReports();
      toast.success("Relatorio mensal enviado por e-mail!");
    } catch {
      toast.error("Falha ao disparar relatorio mensal.");
    } finally {
      setDispatching(false);
    }
  };

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Relatorios</h2>
          <p className="text-sm text-lovable-ink-muted">Gere exports PDF por dashboard e dispare o consolidado mensal.</p>
        </div>
        <Button variant="primary" onClick={() => void handleDispatchMonthly()} disabled={dispatching}>
          <Send size={14} />
          {dispatching ? "Enviando..." : "Disparar Relatorio Mensal"}
        </Button>
      </header>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {REPORT_CARDS.map((card) => {
          const Icon = card.icon;
          const isLoading = loadingByType[card.type];

          return (
            <Card key={card.type}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Icon size={18} className="text-lovable-primary" />
                  {card.title}
                </CardTitle>
                <CardDescription>{card.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  variant="secondary"
                  size="sm"
                  className="w-full"
                  onClick={() => void handleDownload(card.type)}
                  disabled={isLoading}
                >
                  {isLoading ? "Gerando..." : "Baixar PDF"}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
