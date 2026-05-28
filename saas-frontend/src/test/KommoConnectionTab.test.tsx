import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { KommoConnectionTab } from "../components/settings/KommoConnectionTab";
import { kommoSettingsService } from "../services/kommoSettingsService";
import type { KommoSettings } from "../types";

vi.mock("../services/kommoSettingsService", () => ({
  kommoSettingsService: {
    getSettings: vi.fn(),
    updateSettings: vi.fn(),
    testConnection: vi.fn(),
    testNativeFileUpload: vi.fn(),
  },
}));

vi.mock("react-hot-toast", () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

function settings(overrides: Partial<KommoSettings> = {}): KommoSettings {
  return {
    kommo_enabled: true,
    kommo_base_url: "https://crm.kommo.example",
    kommo_has_access_token: true,
    kommo_default_pipeline_id: null,
    kommo_default_stage_id: null,
    kommo_default_responsible_user_id: null,
    automatic_handoff_ready: true,
    primary_message_channel: "kommo",
    kommo_operator_confirmed_send_enabled: true,
    kommo_auto_close_enabled: true,
    kommo_fallback_channel: "whatsapp",
    domain_routes: [],
    trainer_routes: [
      {
        trainer_user_id: "trainer-1",
        trainer_name: "Professor Bruno",
        is_enabled: true,
        route_status: "ready",
        missing_fields: [],
        ready_for_messages: true,
        ready_for_native_pdf: true,
        ready_for_link_pdf: false,
        pipeline_id: "900",
        stage_id: "901",
        salesbot_id: "902",
        channel_source_id: null,
        responsible_user_id: "903",
        message_field_id: "904",
        pdf_url_field_id: null,
        pdf_delivery_mode: "native_file_required",
        file_uuid_field_id: null,
        file_name_field_id: null,
        file_attachment_note_field_id: null,
        source_type_field_id: null,
        source_id_field_id: null,
        tags: ["professor"],
      },
    ],
    ...overrides,
  };
}

function renderTab() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <KommoConnectionTab />
    </QueryClientProvider>,
  );
}

describe("KommoConnectionTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(kommoSettingsService.updateSettings).mockImplementation(async (payload) => settings({ trainer_routes: payload.trainer_routes ?? [] }));
  });

  it("renders trainer pipeline routes and saves them in the Kommo payload", async () => {
    vi.mocked(kommoSettingsService.getSettings).mockResolvedValue(settings());

    renderTab();

    expect(await screen.findByText("Pipelines por professor")).toBeInTheDocument();
    expect(await screen.findByText("Professor Bruno")).toBeInTheDocument();
    expect(screen.getByText("1/1 professores prontos")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByDisplayValue("900")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "Salvar configuracao" }));

    await waitFor(() => {
      expect(kommoSettingsService.updateSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          trainer_routes: expect.arrayContaining([
            expect.objectContaining({
              trainer_user_id: "trainer-1",
              pipeline_id: "900",
              stage_id: "901",
              salesbot_id: "902",
            }),
          ]),
        }),
      );
    });
  });

  it("shows incomplete trainer routes without blocking the page", async () => {
    vi.mocked(kommoSettingsService.getSettings).mockResolvedValue(
      settings({
        trainer_routes: [
          {
            ...settings().trainer_routes[0],
            route_status: "incomplete",
            ready_for_messages: false,
            pipeline_id: null,
            stage_id: null,
            salesbot_id: null,
            missing_fields: ["pipeline_id", "stage_id", "salesbot_id"],
          },
        ],
      }),
    );

    renderTab();

    expect(await screen.findByText("Pipelines por professor")).toBeInTheDocument();
    expect(screen.getByText("1 incompletos")).toBeInTheDocument();
    expect(screen.getAllByText(/Falta pipeline, etapa, salesbot/i).length).toBeGreaterThan(0);
  });
});
