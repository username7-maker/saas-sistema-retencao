import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, Download, FileUp } from "lucide-react";

import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input } from "../../components/ui2";
import {
  publicDiagnosticService,
  type PublicDiagnosisInput,
  type PublicDiagnosisQueuedResponse,
} from "../../services/publicDiagnosticService";


function getErrorMessage(error: unknown): string {
  if (typeof error === "object" && error !== null) {
    const maybeAxios = error as {
      response?: {
        data?: {
          detail?: string | Array<{ msg?: string }>;
          message?: string;
        } | string;
      };
    };
    const data = maybeAxios.response?.data;
    if (typeof data === "string" && data.trim()) {
      return data;
    }
    if (typeof data === "object" && data !== null) {
      if (typeof data.detail === "string" && data.detail.trim()) {
        return data.detail;
      }
      if (Array.isArray(data.detail) && data.detail.length > 0 && data.detail[0]?.msg) {
        return data.detail[0].msg;
      }
      if (typeof data.message === "string" && data.message.trim()) {
        return data.message;
      }
    }
  }
  return "Nao foi possivel processar o diagnostico.";
}

export function DiagnosticoPage() {
  const [form, setForm] = useState({
    fullName: "",
    email: "",
    whatsapp: "",
    gymName: "",
    totalMembers: "",
    avgMonthlyFee: "",
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [lastSuccess, setLastSuccess] = useState<PublicDiagnosisQueuedResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  const mutation = useMutation({
    mutationFn: (payload: PublicDiagnosisInput) => publicDiagnosticService.submitDiagnosis(payload),
    onSuccess: (response) => {
      setLastSuccess(response);
      setErrorMessage("");
      setForm({
        fullName: "",
        email: "",
        whatsapp: "",
        gymName: "",
        totalMembers: "",
        avgMonthlyFee: "",
      });
      setSelectedFile(null);
    },
    onError: (error) => {
      setLastSuccess(null);
      setErrorMessage(getErrorMessage(error));
    },
  });

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedFile) {
      setErrorMessage("Selecione um arquivo CSV com os check-ins.");
      return;
    }

    mutation.mutate({
      fullName: form.fullName.trim(),
      email: form.email.trim(),
      whatsapp: form.whatsapp.trim(),
      gymName: form.gymName.trim(),
      totalMembers: Number(form.totalMembers),
      avgMonthlyFee: Number(form.avgMonthlyFee),
      csvFile: selectedFile,
    });
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(17,178,142,0.16),_transparent_30%),linear-gradient(135deg,#f4efe7_0%,#fbfaf7_44%,#eaf5f2_100%)] px-6 py-10 text-lovable-ink">
      <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="space-y-6">
          <div className="space-y-4">
            <span className="inline-flex rounded-full border border-lovable-border bg-lovable-surface/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-lovable-primary">
              Diagnostico Gratuito
            </span>
            <h1 className="max-w-2xl font-heading text-4xl font-bold leading-tight md:text-5xl">
              Descubra em minutos quanto churn sua academia pode estar deixando passar.
            </h1>
            <p className="max-w-2xl text-base text-lovable-ink-muted md:text-lg">
              Envie um CSV simples de check-ins e receba por email e WhatsApp um diagnostico com alunos em risco,
              MRR ameaçado e potencial de recuperacao.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <Card className="border-0 bg-lovable-surface/75 backdrop-blur">
              <CardHeader>
                <CardTitle className="text-base">Risco simplificado</CardTitle>
                <CardDescription>Vermelho, amarelo e verde com base em inatividade e queda de frequencia.</CardDescription>
              </CardHeader>
            </Card>
            <Card className="border-0 bg-lovable-surface/75 backdrop-blur">
              <CardHeader>
                <CardTitle className="text-base">MRR em risco</CardTitle>
                <CardDescription>Projecao anual de perda e benchmark de recuperacao em linguagem executiva.</CardDescription>
              </CardHeader>
            </Card>
            <Card className="border-0 bg-lovable-surface/75 backdrop-blur">
              <CardHeader>
                <CardTitle className="text-base">Proximo passo</CardTitle>
                <CardDescription>Se fizer sentido, o relatorio ja vem preparado para evoluir para a demo comercial.</CardDescription>
              </CardHeader>
            </Card>
          </div>
        </section>

        <Card className="border-0 bg-lovable-surface/88 shadow-[0_30px_90px_rgba(17,23,33,0.14)] backdrop-blur">
          <CardHeader className="space-y-2">
            <CardTitle className="text-2xl">Solicitar diagnostico</CardTitle>
            <CardDescription>
              O processamento e assicrono. Normalmente o resultado chega em alguns minutos.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div className="grid gap-4 md:grid-cols-2">
                <Input
                  placeholder="Nome do responsavel"
                  value={form.fullName}
                  onChange={(event) => setForm((current) => ({ ...current, fullName: event.target.value }))}
                  required
                />
                <Input
                  type="email"
                  placeholder="Email"
                  value={form.email}
                  onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
                  required
                />
                <Input
                  placeholder="WhatsApp"
                  value={form.whatsapp}
                  onChange={(event) => setForm((current) => ({ ...current, whatsapp: event.target.value }))}
                  required
                />
                <Input
                  placeholder="Nome da academia"
                  value={form.gymName}
                  onChange={(event) => setForm((current) => ({ ...current, gymName: event.target.value }))}
                  required
                />
                <Input
                  type="number"
                  min={1}
                  placeholder="Total de alunos"
                  value={form.totalMembers}
                  onChange={(event) => setForm((current) => ({ ...current, totalMembers: event.target.value }))}
                  required
                />
                <Input
                  type="number"
                  min={0}
                  step="0.01"
                  placeholder="Mensalidade media"
                  value={form.avgMonthlyFee}
                  onChange={(event) => setForm((current) => ({ ...current, avgMonthlyFee: event.target.value }))}
                  required
                />
              </div>

              <div className="rounded-2xl border border-dashed border-lovable-border bg-lovable-surface-soft/70 p-4">
                <label className="block text-sm font-medium text-lovable-ink">CSV de check-ins</label>
                <p className="mt-1 text-xs text-lovable-ink-muted">
                  O arquivo deve conter coluna de aluno e data/hora do check-in. Aceitamos colunas flexiveis.
                </p>
                <input
                  className="mt-3 block w-full rounded-xl border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink file:mr-4 file:rounded-lg file:border-0 file:bg-lovable-primary file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white"
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(event) => {
                    setSelectedFile(event.target.files?.[0] ?? null);
                    setErrorMessage("");
                  }}
                  required
                />
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <span className="text-sm text-lovable-ink-muted">
                    {selectedFile ? selectedFile.name : "Nenhum arquivo selecionado"}
                  </span>
                  <a
                    className="inline-flex items-center gap-2 text-sm font-semibold text-lovable-primary hover:underline"
                    href="/template_checkins.csv"
                    download
                  >
                    <Download size={16} />
                    Baixar template
                  </a>
                </div>
              </div>

              {mutation.isPending && (
                <div className="flex items-center gap-3 rounded-2xl border border-lovable-border bg-lovable-primary-soft px-4 py-3 text-sm text-lovable-ink">
                  <FileUp size={18} className="text-lovable-primary" />
                  Processando seu diagnostico...
                </div>
              )}

              {lastSuccess && (
                <div className="flex items-start gap-3 rounded-2xl border border-[hsl(var(--lovable-success)/0.25)] bg-[hsl(var(--lovable-success)/0.12)] px-4 py-3 text-sm text-lovable-ink">
                  <CheckCircle2 size={18} className="mt-0.5 text-[hsl(var(--lovable-success))]" />
                  <div>
                    <p className="font-semibold">Diagnostico enviado.</p>
                    <p>Verifique seu email e WhatsApp em alguns minutos.</p>
                  </div>
                </div>
              )}

              {errorMessage && (
                <div className="flex items-start gap-3 rounded-2xl border border-[hsl(var(--lovable-danger)/0.25)] bg-[hsl(var(--lovable-danger)/0.1)] px-4 py-3 text-sm text-lovable-ink">
                  <AlertCircle size={18} className="mt-0.5 text-[hsl(var(--lovable-danger))]" />
                  <div>
                    <p className="font-semibold">Nao foi possivel concluir.</p>
                    <p>{errorMessage}</p>
                  </div>
                </div>
              )}

              <Button className="w-full" size="lg" type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "Processando..." : "Receber diagnostico"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
