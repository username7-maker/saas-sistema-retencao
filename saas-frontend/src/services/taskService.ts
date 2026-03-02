import { api } from "./api";
import type { PaginatedResponse, Task } from "../types";

export interface CreateTaskPayload {
  member_id?: string;
  lead_id?: string;
  title: string;
  description?: string;
  priority: Task["priority"];
  status: Task["status"];
  due_date?: string | null;
  suggested_message?: string | null;
  assigned_to_user_id?: string | null;
}

export interface UpdateTaskPayload {
  title?: string;
  description?: string | null;
  priority?: Task["priority"];
  status?: Task["status"];
  kanban_column?: string;
  due_date?: string | null;
  suggested_message?: string | null;
  assigned_to_user_id?: string | null;
  extra_data?: Record<string, unknown>;
}

const PAGE_SIZE = 50;

export const taskService = {
  async listTasks(): Promise<PaginatedResponse<Task>> {
    return taskService.listAllTasks();
  },

  async listAllTasks(): Promise<PaginatedResponse<Task>> {
    const first = await api
      .get<PaginatedResponse<Task>>("/api/v1/tasks", { params: { page: 1, page_size: PAGE_SIZE } })
      .then((r) => r.data);

    if (first.total <= PAGE_SIZE) return first;

    const totalPages = Math.ceil(first.total / PAGE_SIZE);
    const rest = await Promise.all(
      Array.from({ length: totalPages - 1 }, (_, i) =>
        api
          .get<PaginatedResponse<Task>>("/api/v1/tasks", { params: { page: i + 2, page_size: PAGE_SIZE } })
          .then((r) => r.data.items),
      ),
    );

    return { ...first, items: [...first.items, ...rest.flat()] };
  },

  async createTask(payload: CreateTaskPayload): Promise<Task> {
    const { data } = await api.post<Task>("/api/v1/tasks/", payload);
    return data;
  },

  async updateTask(taskId: string, payload: UpdateTaskPayload): Promise<Task> {
    const { data } = await api.patch<Task>(`/api/v1/tasks/${taskId}`, payload);
    return data;
  },

  async deleteTask(taskId: string): Promise<void> {
    await api.delete(`/api/v1/tasks/${taskId}`);
  },
};
