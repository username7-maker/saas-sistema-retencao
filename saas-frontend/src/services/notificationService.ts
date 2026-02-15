import { api } from "./api";
import type { InAppNotification, PaginatedResponse } from "../types";

export const notificationService = {
  async listNotifications(params?: { unread_only?: boolean; include_all?: boolean }): Promise<PaginatedResponse<InAppNotification>> {
    const { data } = await api.get<PaginatedResponse<InAppNotification>>("/api/v1/notifications", {
      params: {
        page_size: 50,
        unread_only: params?.unread_only ?? false,
        include_all: params?.include_all ?? false,
      },
    });
    return data;
  },

  async markRead(notificationId: string, read = true): Promise<InAppNotification> {
    const { data } = await api.patch<InAppNotification>(`/api/v1/notifications/${notificationId}/read`, { read });
    return data;
  },
};
