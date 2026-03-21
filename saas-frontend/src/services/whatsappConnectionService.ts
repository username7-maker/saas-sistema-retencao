import { api } from "./api";

export interface WhatsAppStatus {
  status: "disconnected" | "connecting" | "connected" | "error";
  phone: string | null;
  connected_at: string | null;
  instance: string | null;
}

export interface QRCodeData {
  status: "connecting" | "connected" | "error";
  qrcode: string | null;
}

export const whatsappConnectionService = {
  async getStatus(): Promise<WhatsAppStatus> {
    const { data } = await api.get<WhatsAppStatus>("/api/v1/whatsapp/status");
    return data;
  },

  async connect(): Promise<QRCodeData> {
    const { data } = await api.post<QRCodeData>("/api/v1/whatsapp/connect");
    return data;
  },

  async getQR(): Promise<QRCodeData> {
    const { data } = await api.get<QRCodeData>("/api/v1/whatsapp/qr");
    return data;
  },

  async disconnect(): Promise<void> {
    await api.delete("/api/v1/whatsapp/disconnect");
  },
};
