import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import {
  Button,
  CommandCard,
  Table,
  TableInner,
  TableHead,
  TableBody,
  TableRow,
  TableHeaderCell,
  TableCell,
} from "../../components/ui2";
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
      <CommandCard variant="elevated">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.3em] text-blue-400">Sistema</p>
            <h2 className="mt-1 font-heading text-3xl font-bold md:text-4xl">
              <span className="bg-gradient-to-r from-white via-white to-blue-300 bg-clip-text text-transparent">
                Notificações
              </span>
            </h2>
            <p className="mt-1 text-sm text-lovable-ink-muted">Alertas internos de retenção, operação e acompanhamento comercial.</p>
          </div>
          {unread > 0 && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-lovable-warning/30 bg-lovable-warning/10 px-3 py-1.5 text-xs font-semibold text-lovable-warning">
              {unread} não {unread === 1 ? "lida" : "lidas"}
            </span>
          )}
        </div>
      </CommandCard>

      {!hasItems ? (
        <CommandCard>
          <div className="py-6 text-center">
            <p className="text-sm font-semibold text-lovable-ink">Nenhuma notificação por enquanto.</p>
            <p className="mt-1 text-sm text-lovable-ink-muted">
              Quando o sistema gerar alertas compartilhados ou avisos operacionais, eles aparecerão aqui.
            </p>
          </div>
        </CommandCard>
      ) : (
        <Table>
          <div className="overflow-x-auto">
            <TableInner>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Categoria</TableHeaderCell>
                  <TableHeaderCell>Título</TableHeaderCell>
                  <TableHeaderCell>Mensagem</TableHeaderCell>
                  <TableHeaderCell>Criada em</TableHeaderCell>
                  <TableHeaderCell>Status</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {notificationsQuery.data.items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="uppercase text-xs text-lovable-ink-muted">{item.category}</TableCell>
                    <TableCell className="font-medium">{item.title}</TableCell>
                    <TableCell className="text-lovable-ink-muted">{item.message}</TableCell>
                    <TableCell className="whitespace-nowrap text-lovable-ink-muted">{new Date(item.created_at).toLocaleString("pt-BR")}</TableCell>
                    <TableCell>
                      {item.read_at ? (
                        <span className="rounded-full bg-lovable-success/15 px-2 py-1 text-xs font-semibold text-lovable-success">Lida</span>
                      ) : (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => markReadMutation.mutate(item.id)}
                          disabled={markReadMutation.isPending}
                        >
                          Marcar como lida
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </TableInner>
          </div>
        </Table>
      )}
    </section>
  );
}
