import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";

import { messageComposerService } from "../../services/messageComposerService";
import { getHttpErrorDetail } from "../../utils/httpErrors";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Select, Textarea } from "../ui2";

export function MessageTemplatesSettingsTab() {
  const queryClient = useQueryClient();
  const templatesQuery = useQuery({ queryKey: ["message-templates"], queryFn: messageComposerService.listTemplates });
  const [selectedKey, setSelectedKey] = useState("");
  const [content, setContent] = useState("");
  const templates = templatesQuery.data ?? [];
  const selected = templates.find((item) => item.key === selectedKey) ?? templates[0] ?? null;

  useEffect(() => {
    if (selected && selected.key !== selectedKey) setSelectedKey(selected.key);
  }, [selected, selectedKey]);

  useEffect(() => {
    if (selected) setContent(selected.content);
  }, [selected]);

  const saveMutation = useMutation({
    mutationFn: () => messageComposerService.updateTemplate(selected!.key, content),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["message-templates"] });
      toast.success("Mensagem pronta atualizada para esta academia.");
    },
    onError: (error) => toast.error(getHttpErrorDetail(error, "Não foi possível salvar a mensagem pronta.")),
  });
  const restoreMutation = useMutation({
    mutationFn: () => messageComposerService.restoreTemplate(selected!.key),
    onSuccess: (item) => {
      setContent(item.content);
      void queryClient.invalidateQueries({ queryKey: ["message-templates"] });
      toast.success("Padrão restaurado.");
    },
    onError: (error) => toast.error(getHttpErrorDetail(error, "Não foi possível restaurar o padrão.")),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Mensagens prontas</CardTitle>
        <p className="text-sm text-lovable-ink-muted">Estas mensagens são usadas sem custo de IA. A IA só entra quando o operador clicar em “Melhorar com IA”.</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {templatesQuery.isLoading ? <p className="text-sm text-lovable-ink-muted">Carregando mensagens...</p> : null}
        {selected ? (
          <>
            <Select value={selected.key} onChange={(event) => setSelectedKey(event.target.value)}>
              {templates.map((item) => <option key={item.key} value={item.key}>{item.domain} — {item.objective}</option>)}
            </Select>
            <div className="flex flex-wrap gap-2">
              <Badge variant={selected.origin === "template_gym_override" ? "info" : "neutral"}>{selected.origin === "template_gym_override" ? "Personalizada pela academia" : "Padrão Cordex"}</Badge>
              <Badge variant="neutral">v{selected.version}</Badge>
            </div>
            <Textarea value={content} onChange={(event) => setContent(event.target.value)} rows={6} />
            <p className="text-xs text-lovable-ink-muted">Variáveis permitidas: {selected.allowed_variables.map((item) => `{${item}}`).join(", ")}</p>
            <div className="flex flex-wrap gap-2">
              <Button variant="primary" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending || !content.trim()}>Salvar para a academia</Button>
              <Button variant="secondary" onClick={() => restoreMutation.mutate()} disabled={restoreMutation.isPending || selected.origin !== "template_gym_override"}>Restaurar padrão</Button>
            </div>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
