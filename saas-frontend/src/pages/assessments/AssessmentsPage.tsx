import { useQuery } from "@tanstack/react-query";

import { AssessmentOperationsBoard } from "../../components/assessments/AssessmentOperationsBoard";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { assessmentService } from "../../services/assessmentService";

export function AssessmentsPage() {
  const dashboardQuery = useQuery({
    queryKey: ["assessments", "dashboard"],
    queryFn: () => assessmentService.dashboard(),
    staleTime: 5 * 60 * 1000,
  });

  if (dashboardQuery.isLoading) {
    return <LoadingPanel text="Carregando central operacional de avaliacoes..." />;
  }

  if (dashboardQuery.isError) {
    return <LoadingPanel text="Erro ao carregar avaliacoes. Tente novamente." />;
  }

  if (!dashboardQuery.data) {
    return <LoadingPanel text="Sem dados de avaliacoes." />;
  }

  return <AssessmentOperationsBoard dashboard={dashboardQuery.data} />;
}
