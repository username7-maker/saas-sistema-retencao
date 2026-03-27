import { api } from "./api";
import type { AIAssistantPayload, PaginatedResponse, Task } from "../types";

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
type ListTaskParams = { page?: number; page_size?: number; include_retention?: boolean };

export const taskService = {
  async listTasks(params?: ListTaskParams): Promise<PaginatedResponse<Task>> {
    const { page = 1, page_size = PAGE_SIZE, include_retention = false } = params ?? {};
    const { data } = await api.get<PaginatedResponse<Task>>("/api/v1/tasks/", {
      params: { page, page_size, include_retention },
    });
    return data;
  },

  async listAllTasks(params?: Pick<ListTaskParams, "include_retention">): Promise<PaginatedResponse<Task>> {
    const include_retention = params?.include_retention ?? false;
    const first = await taskService.listTasks({ page: 1, page_size: PAGE_SIZE, include_retention });

    if (first.total <= PAGE_SIZE) return first;

    const totalPages = Math.ceil(first.total / PAGE_SIZE);
    const rest: Task[] = [];
    for (let page = 2; page <= totalPages; page += 1) {
      const response = await taskService.listTasks({ page, page_size: PAGE_SIZE, include_retention });
      rest.push(...response.items);
    }

    return { ...first, items: [...first.items, ...rest] };
  },

  async createTask(payload: CreateTaskPayload): Promise<Task> {
    const { data } = await api.post<Task>("/api/v1/tasks/", payload);
    return data;
  },

  async updateTask(taskId: string, payload: UpdateTaskPayload): Promise<Task> {
    const { data } = await api.patch<Task>(`/api/v1/tasks/${taskId}`, payload);
    return data;
  },

  async getAssistant(taskId: string): Promise<AIAssistantPayload> {
    const { data } = await api.get<AIAssistantPayload>(`/api/v1/tasks/${taskId}/assistant`);
    return data;
  },

  async deleteTask(taskId: string): Promise<void> {
    await api.delete(`/api/v1/tasks/${taskId}`);
  },
};
