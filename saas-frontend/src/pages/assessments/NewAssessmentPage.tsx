import { Activity, Ruler, Scale } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { Button, Card, CardContent } from "../../components/ui2";

export function NewAssessmentPage() {
  const { memberId } = useParams<{ memberId: string }>();
  const navigate = useNavigate();

  if (!memberId) {
    return <LoadingPanel text="Membro nao informado." />;
  }

  return (
    <section className="mx-auto max-w-5xl space-y-4 p-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Nova avaliacao</p>
        <h1 className="mt-1 font-heading text-2xl font-bold text-lovable-ink">Escolha o modo de avaliacao</h1>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardContent className="space-y-4 pt-5">
            <div className="flex items-center gap-3">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-lovable-border bg-lovable-surface-soft">
                <Scale size={18} />
              </span>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Fluxo legado</p>
                <h2 className="font-heading text-lg font-bold text-lovable-ink">Com bioimpedancia</h2>
              </div>
            </div>
            <p className="text-sm text-lovable-ink-muted">Abre a aba atual da balanca, OCR, camera e revisao existentes.</p>
            <Button type="button" variant="primary" onClick={() => navigate(`/assessments/members/${memberId}?tab=bioimpedancia`)}>
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
                <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Modo local</p>
                <h2 className="font-heading text-lg font-bold text-lovable-ink">Sem bioimpedancia</h2>
              </div>
            </div>
            <p className="text-sm text-lovable-ink-muted">Abre o formulario antropometrico com calculo no backend e PDF local.</p>
            <Button
              type="button"
              variant="secondary"
              onClick={() => navigate(`/assessments/members/${memberId}?tab=registro&mode=manual_anthropometry`)}
            >
              <Activity size={14} />
              Sem bioimpedancia
            </Button>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
