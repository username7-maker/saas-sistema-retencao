import { useQuery } from "@tanstack/react-query";
import { DollarSign, TrendingUp, Users } from "lucide-react";
import { api } from "../../services/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui2";
import { Skeleton } from "../ui2/Skeleton";

interface RoiSummary {
  period_days: number;
  total_automated: number;
  reengaged_count: number;
  reengagement_rate: number;
  preserved_revenue: number;
}

export function RoiSummaryCard() {
  const { data, isLoading } = useQuery({
    queryKey: ["roi-summary"],
    queryFn: async () => {
      const res = await api.get<RoiSummary>("/api/v1/roi/summary");
      return res.data;
    },
    staleTime: 10 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-4 w-40" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  const hasData = data && data.total_automated > 0;

  return (
    <Card className="border border-lovable-border bg-[linear-gradient(135deg,hsl(var(--lovable-surface)),hsl(var(--lovable-surface-soft)))]">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl">
          <TrendingUp size={18} className="text-lovable-primary" />
          ROI das Automacoes
        </CardTitle>
        <CardDescription>
          Receita preservada por acoes automaticas nos ultimos 30 dias
        </CardDescription>
      </CardHeader>
      <CardContent>
        {hasData ? (
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-lovable-ink">
                {new Intl.NumberFormat("pt-BR", {
                  style: "currency",
                  currency: "BRL",
                  maximumFractionDigits: 0,
                }).format(data.preserved_revenue)}
              </p>
              <p className="text-xs text-lovable-ink-muted flex items-center justify-center gap-1">
                <DollarSign size={12} /> Receita preservada
              </p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-lovable-ink">
                {data.reengaged_count}
              </p>
              <p className="text-xs text-lovable-ink-muted flex items-center justify-center gap-1">
                <Users size={12} /> Reengajados
              </p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-lovable-ink">
                {data.reengagement_rate}%
              </p>
              <p className="text-xs text-lovable-ink-muted">Taxa de retorno</p>
            </div>
          </div>
        ) : (
          <p className="text-sm text-lovable-ink-muted">
            As automacoes estao ativas! Em breve os primeiros resultados
            aparecerao aqui. O tempo medio para o primeiro reengajamento e de 7
            dias.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
