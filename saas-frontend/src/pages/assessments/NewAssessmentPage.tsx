import { Navigate, useParams } from "react-router-dom";

import { LoadingPanel } from "../../components/common/LoadingPanel";

export function NewAssessmentPage() {
  const { memberId } = useParams<{ memberId: string }>();

  if (!memberId) {
    return <LoadingPanel text="Membro nao informado." />;
  }

  return <Navigate to={`/assessments/members/${memberId}?tab=registro`} replace />;
}
