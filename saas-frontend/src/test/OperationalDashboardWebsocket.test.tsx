import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { OperationalDashboardPage } from "../pages/dashboard/OperationalDashboardPage";

vi.mock("../hooks/useDashboard", () => ({
  useOperationalDashboard: () => ({
    isLoading: false,
    isError: false,
    data: {
      realtime_checkins: 0,
      heatmap: [],
      inactive_7d_total: 0,
      inactive_7d_items: [],
      birthday_today_total: 0,
      birthday_today_items: [],
    },
    refetch: vi.fn(),
    error: null,
  }),
}));

vi.mock("../services/storage", () => ({
  tokenStorage: {
    getAccessToken: () => "jwt-token",
  },
}));

vi.mock("../services/runtimeConfig", () => ({
  WS_BASE_URL: "wss://pilot.example.com",
}));

vi.mock("../components/charts/HeatmapGrid", () => ({
  HeatmapGrid: () => <div>Heatmap mock</div>,
}));

vi.mock("../components/common/AiInsightCard", () => ({
  AiInsightCard: () => <div>Insight mock</div>,
}));

vi.mock("../components/common/DashboardActions", () => ({
  DashboardActions: () => <div>Actions mock</div>,
}));

vi.mock("../components/common/QuickActions", () => ({
  QuickActions: () => <div>Quick actions mock</div>,
}));

describe("OperationalDashboardPage websocket auth", () => {
  it("opens the websocket without token in the URL and authenticates via first message", () => {
    const send = vi.fn();
    const close = vi.fn();
    const sockets: Array<{
      onopen: (() => void) | null;
      onclose: (() => void) | null;
      onerror: (() => void) | null;
      onmessage: ((event: MessageEvent<string>) => void) | null;
      send: typeof send;
      close: typeof close;
    }> = [];

    class WebSocketMock {
      onopen: (() => void) | null = null;
      onclose: (() => void) | null = null;
      onerror: (() => void) | null = null;
      onmessage: ((event: MessageEvent<string>) => void) | null = null;
      send = send;
      close = close;

      constructor(_: string) {
        sockets.push(this);
      }
    }

    const webSocketSpy = vi.spyOn(globalThis, "WebSocket").mockImplementation(WebSocketMock as unknown as typeof WebSocket);

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <OperationalDashboardPage />
      </QueryClientProvider>,
    );

    expect(webSocketSpy).toHaveBeenCalledWith("wss://pilot.example.com/ws/updates");

    act(() => {
      sockets[0]?.onopen?.();
    });

    expect(send).toHaveBeenCalledWith(JSON.stringify({ type: "auth", token: "jwt-token" }));
    expect(webSocketSpy.mock.calls[0]?.[0]).not.toContain("token=");

    webSocketSpy.mockRestore();
  });
});
