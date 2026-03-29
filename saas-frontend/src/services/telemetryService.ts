import { api } from "./api";

interface TrackUiEventInput {
  event_name: string;
  surface: string;
  details?: Record<string, unknown>;
}

export const telemetryService = {
  async track(payload: TrackUiEventInput): Promise<void> {
    if (import.meta.env.MODE === "test") return;

    try {
      await api.post("/api/v1/audit/events", {
        event_name: payload.event_name,
        surface: payload.surface,
        details: payload.details ?? {},
      });
    } catch {
      // Telemetry nunca deve interromper o fluxo operacional principal.
    }
  },
};
