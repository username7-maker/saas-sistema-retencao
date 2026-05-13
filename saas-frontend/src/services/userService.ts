import { api } from "./api";

export type StaffWorkShift = "overnight" | "morning" | "afternoon" | "evening";

export interface StaffUser {
  id: string;
  gym_id: string;
  full_name: string;
  email: string;
  role: "owner" | "manager" | "receptionist" | "salesperson" | "trainer";
  is_active: boolean;
  job_title?: string | null;
  work_shift?: StaffWorkShift | null;
  work_shift_scope?: StaffWorkShift[] | null;
  avatar_url?: string | null;
  created_at: string;
}

export interface UserCreatePayload {
  full_name: string;
  email: string;
  password: string;
  role: StaffUser["role"];
  job_title?: string | null;
  work_shift?: StaffUser["work_shift"];
  work_shift_scope?: StaffUser["work_shift_scope"];
  avatar_url?: string | null;
}

export interface UserUpdatePayload {
  full_name?: string;
  email?: string;
  is_active?: boolean;
  job_title?: string | null;
  work_shift?: StaffUser["work_shift"];
  work_shift_scope?: StaffUser["work_shift_scope"];
  avatar_url?: string | null;
  role?: StaffUser["role"];
}

export interface UserProfileUpdatePayload {
  full_name?: string;
  job_title?: string | null;
  work_shift?: StaffUser["work_shift"];
  work_shift_scope?: StaffUser["work_shift_scope"];
  avatar_url?: string | null;
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

  async updateUserProfile(userId: string, payload: UserProfileUpdatePayload): Promise<StaffUser> {
    const { data } = await api.patch<StaffUser>(`/api/v1/users/${userId}/profile`, payload);
    return data;
  },

  async updateMyProfile(payload: UserProfileUpdatePayload): Promise<StaffUser> {
    const { data } = await api.patch<StaffUser>("/api/v1/users/me/profile", payload);
    return data;
  },

  async uploadMyAvatar(file: File): Promise<StaffUser> {
    const formData = new FormData();
    formData.append("file", file);
    const { data } = await api.post<StaffUser>("/api/v1/users/me/avatar", formData);
    return data;
  },

  async setUserActive(userId: string, is_active: boolean): Promise<StaffUser> {
    const { data } = await api.patch<StaffUser>(`/api/v1/users/${userId}/activation`, { is_active });
    return data;
  },
};
