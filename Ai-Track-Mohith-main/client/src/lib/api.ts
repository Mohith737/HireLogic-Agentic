import axios from "axios";
import { clearAuth, getStoredUser } from "./auth";

const BASE_URL = import.meta.env.VITE_API_URL ?? "";

const client = axios.create({
  baseURL: BASE_URL,
});

client.interceptors.request.use((config) => {
  const user = getStoredUser();
  if (user?.token) {
    config.headers.Authorization = `Bearer ${user.token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error?.response?.status === 401) {
      clearAuth();
      window.location.href = "/login";
    }
    throw error;
  },
);

export async function api<T>(
  path: string,
  options?: { method?: string; data?: unknown },
): Promise<T> {
  const response = await client.request<T>({
    url: path,
    method: options?.method ?? "GET",
    data: options?.data,
  });
  return response.data;
}

export default client;
