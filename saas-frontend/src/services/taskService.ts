import { api } from "./api";
import type { PaginatedResponse, Task } from "../types";

export interface CreateTaskPayload {
  member_id: string;
  title: string;
  description?: string;
  priority: Task["priority"];
  status: Task["status"];
}

export const taskService = {
  async listTasks(): Promise<PaginatedResponse<Task>> {
    const { data } = await api.get<PaginatedResponse<Task>>("/api/v1/tasks", {
      params: { page_size: 100 },
    });
    return data;
  },

  async createTask(payload: CreateTaskPayload): Promise<Task> {
    const { data } = await api.post<Task>("/api/v1/tasks/", payload);
    return data;
  },

  async updateTask(taskId: string, status: Task["status"]): Promise<Task> {
    const { data } = await api.patch<Task>(`/api/v1/tasks/${taskId}`, { status });
    return data;
  },
};
