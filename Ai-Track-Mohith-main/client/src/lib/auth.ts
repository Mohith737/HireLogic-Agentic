import { useQuery } from "@tanstack/react-query";
import client from "./api";

export interface StoredUser {
  id: number;
  username: string;
  token: string;
  token_expires_at?: string;
  email?: string;
  full_name?: string | null;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: Omit<StoredUser, "token" | "token_expires_at">;
}

export async function loginWithPassword(
  username: string,
  password: string,
): Promise<StoredUser> {
  const response = await client.post<AuthResponse>("/auth/login", {
    username,
    password,
  });
  const storedUser: StoredUser = {
    ...response.data.user,
    token: response.data.access_token,
  };
  localStorage.setItem("token", response.data.access_token);
  localStorage.setItem("user", JSON.stringify(storedUser));
  return storedUser;
}

export function getStoredUser(): StoredUser | null {
  try {
    const raw = localStorage.getItem("user");
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredUser;
    if (!parsed?.token || typeof parsed.token !== "string" || parsed.token.trim() === "") {
      localStorage.removeItem("user");
      localStorage.removeItem("token");
      return null;
    }
    if (parsed.token_expires_at) {
      const expiry = new Date(parsed.token_expires_at);
      if (expiry <= new Date()) {
        localStorage.removeItem("user");
        localStorage.removeItem("token");
        return null;
      }
    }
    return parsed;
  } catch {
    localStorage.removeItem("user");
    localStorage.removeItem("token");
    return null;
  }
}

export function isAuthenticated(): boolean {
  return getStoredUser() !== null;
}

export function clearAuth(): void {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
}

export function logout(): void {
  clearAuth();
}

export function useAuth() {
  return useQuery<StoredUser | null>({
    queryKey: ["auth-user"],
    queryFn: getStoredUser,
    staleTime: Infinity,
  });
}
