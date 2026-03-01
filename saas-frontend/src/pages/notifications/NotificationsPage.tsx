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

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-lovable-ink">Notificações In-App</h2>
        <p className="text-sm text-lovable-ink-muted">Alertas internos de retenção e operação. Não há envio automático de WhatsApp.</p>
      </header>

      <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        Não lidas: <strong>{unread}</strong>
      </div>

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
                  <td className="px-2 py-2 font-medium text-slate-800">{item.title}</td>
                  <td className="px-2 py-2 text-lovable-ink-muted">{item.message}</td>
                  <td className="px-2 py-2 text-lovable-ink-muted">{new Date(item.created_at).toLocaleString()}</td>
                  <td className="px-2 py-2">
                    {item.read_at ? (
                      <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-700">Lida</span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => markReadMutation.mutate(item.id)}
                        className="rounded-full bg-brand-500 px-2 py-1 text-xs font-semibold text-white hover:bg-brand-700"
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
    </section>
  );
}
