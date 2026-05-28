import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { NotificationsPage } from "../pages/notifications/NotificationsPage";
import { notificationService } from "../services/notificationService";

vi.mock("../services/notificationService", () => ({
  notificationService: {
    listNotifications: vi.fn(),
    markRead: vi.fn(),
  },
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("NotificationsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(notificationService.markRead).mockResolvedValue({
      id: "notification-1",
      user_id: null,
      category: "tasks",
      title: "Follow-up pendente",
      message: "Aluno precisa de retorno.",
      member_id: null,
      read_at: "2026-05-27T12:00:00Z",
      created_at: "2026-05-27T10:00:00Z",
      extra_data: {},
    });
  });

  it("shows a useful empty state when there are no notifications", async () => {
    vi.mocked(notificationService.listNotifications).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 50,
    });

    renderPage();

    expect(await screen.findByText("Nenhuma notificação por enquanto.")).toBeInTheDocument();
    expect(screen.getByText(/alertas compartilhados ou avisos operacionais/i)).toBeInTheDocument();
  });

  it("marks an unread notification as read", async () => {
    vi.mocked(notificationService.listNotifications).mockResolvedValue({
      items: [
        {
          id: "notification-1",
          user_id: null,
          category: "tasks",
          title: "Follow-up pendente",
          message: "Aluno precisa de retorno.",
          member_id: null,
          read_at: null,
          created_at: "2026-05-27T10:00:00Z",
          extra_data: {},
        },
      ],
      total: 1,
      page: 1,
      page_size: 50,
    });

    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "Marcar como lida" }));

    await waitFor(() => {
      expect(notificationService.markRead).toHaveBeenCalledWith("notification-1", true);
    });
  });
});
