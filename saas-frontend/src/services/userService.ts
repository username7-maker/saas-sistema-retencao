import { api } from "./api";

export interface StaffUser {
  id: string;
  gym_id: string;
  full_name: string;
  email: string;
  role: "owner" | "manager" | "receptionist" | "salesperson" | "trainer";
  is_active: boolean;
  created_at: string;
}

export interface UserCreatePayload {
  full_name: string;
  email: string;
  password: string;
  role: StaffUser["role"];
}

export interface UserUpdatePayload {
  is_active?: boolean;
  role?: StaffUser["role"];
}

export const userService = {
  async listUsers(): Promise<StaffUser[]> {
    const { data } = await api.get<StaffUser[]>("/api/v1/users/");
    return data;
  },

  async createUser(payload: UserCreatePayload): Promise<StaffUser> {
    const { data } = await api.post<StaffUser>("/api/v1/users/", payload);
    return data;
  },

  async updateUser(userId: string, payload: UserUpdatePayload): Promise<StaffUser> {
    const { data } = await api.patch<StaffUser>(`/api/v1/users/${userId}`, payload);
    return data;
  },
};
