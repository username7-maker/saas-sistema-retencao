import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { notificationService } from "../../services/notificationService";

export function NotificationsPage() {
  const queryClient = useQueryClient();
  const notificationsQuery = useQuery({
    queryKey: ["notifications"],
    queryFn: () => notificationService.listNotifications({ unread_only: false }),
    staleTime: 5 * 60 * 1000,
  });

  const markReadMutation = useMutation({
    mutationFn: (notificationId: string) => notificationService.markRead(notificationId, true),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
      void queryClient.invalidateQueries({ queryKey: ["notifications", "unread-count"] });
    },
  });

  if (notificationsQuery.isLoading) {
    return <LoadingPanel text="Carregando notificações..." />;
  }

  if (notificationsQuery.isError) {
    return <LoadingPanel text="Erro ao carregar notificações. Tente novamente." />;
  }

  if (!notificationsQuery.data) {
    return <LoadingPanel text="Sem notificações disponíveis." />;
  }

  const unread = notificationsQuery.data.items.filter((item) => item.read_at == null).length;
  const hasItems = notificationsQuery.data.items.length > 0;

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-lovable-ink">Notificações</h2>
        <p className="text-sm text-lovable-ink-muted">Alertas internos de retenção, operação e acompanhamento comercial.</p>
      </header>

      <div className="rounded-xl border border-lovable-warning/30 bg-lovable-warning/10 px-4 py-3 text-sm text-lovable-ink">
        Não lidas: <strong>{unread}</strong>
      </div>

      {!hasItems ? (
        <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-8 text-center shadow-panel">
          <p className="text-sm font-semibold text-lovable-ink">Nenhuma notificação por enquanto.</p>
          <p className="mt-1 text-sm text-lovable-ink-muted">
            Quando o sistema gerar alertas compartilhados ou avisos operacionais, eles aparecerão aqui.
          </p>
        </section>
      ) : (
        <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wider text-lovable-ink-muted">
                <tr>
                  <th className="px-2 py-2">Categoria</th>
                  <th className="px-2 py-2">Título</th>
                  <th className="px-2 py-2">Mensagem</th>
                  <th className="px-2 py-2">Criada em</th>
                  <th className="px-2 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {notificationsQuery.data.items.map((item) => (
                  <tr key={item.id} className="border-t border-lovable-border">
                    <td className="px-2 py-2 uppercase text-xs text-lovable-ink-muted">{item.category}</td>
                    <td className="px-2 py-2 font-medium text-lovable-ink">{item.title}</td>
                    <td className="px-2 py-2 text-lovable-ink-muted">{item.message}</td>
                    <td className="px-2 py-2 text-lovable-ink-muted">{new Date(item.created_at).toLocaleString("pt-BR")}</td>
                    <td className="px-2 py-2">
                      {item.read_at ? (
                        <span className="rounded-full bg-lovable-success/15 px-2 py-1 text-xs font-semibold text-lovable-success">Lida</span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => markReadMutation.mutate(item.id)}
                          className="rounded-full bg-lovable-primary px-2 py-1 text-xs font-semibold text-white hover:opacity-90"
                        >
                          Marcar como lida
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </section>
  );
}
