import type {
  ActuarBridgeDevice,
  ActuarBridgePairingCode,
  ActuarConnectionTestResult,
  ActuarSettings,
  ActuarSettingsUpdateInput,
} from "../types";
import { api } from "./api";

export const actuarSettingsService = {
  async getSettings(): Promise<ActuarSettings> {
    const { data } = await api.get<ActuarSettings>("/api/v1/settings/actuar");
    return data;
  },

  async updateSettings(payload: ActuarSettingsUpdateInput): Promise<ActuarSettings> {
    const { data } = await api.put<ActuarSettings>("/api/v1/settings/actuar", payload);
    return data;
  },

  async testConnection(): Promise<ActuarConnectionTestResult> {
    const { data } = await api.post<ActuarConnectionTestResult>("/api/v1/settings/actuar/test-connection");
    return data;
  },

  async listBridgeDevices(): Promise<ActuarBridgeDevice[]> {
    const { data } = await api.get<ActuarBridgeDevice[]>("/api/v1/settings/actuar/bridge/devices");
    return data;
  },

  async issuePairingCode(): Promise<ActuarBridgePairingCode> {
    const { data } = await api.post<ActuarBridgePairingCode>("/api/v1/settings/actuar/bridge/pairing-code");
    return data;
  },

  async revokeBridgeDevice(deviceId: string): Promise<ActuarBridgeDevice> {
    const { data } = await api.post<ActuarBridgeDevice>(`/api/v1/settings/actuar/bridge/devices/${deviceId}/revoke`);
    return data;
  },
};
