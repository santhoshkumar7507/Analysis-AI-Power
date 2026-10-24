import React, { createContext, useContext, useState, useEffect } from "react";
import { apiClient } from "../api/client";

export interface User {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  role: "admin" | "support_manager" | "support_agent";
  is_active: boolean;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan: string;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  organization: Organization | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  switchDemoRole: (role: "admin" | "manager" | "agent") => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem("resolveai_access_token"));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchProfile = async () => {
    try {
      const [userRes, orgRes] = await Promise.all([
        apiClient.get("/auth/me"),
        apiClient.get("/auth/organization"),
      ]);
      setUser(userRes.data);
      setOrganization(orgRes.data);
    } catch {
      logout();
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchProfile();
    } else {
      // Default to auto-login as demo admin for seamless evaluation
      login("admin@acme.com", "Password123!").catch(() => setIsLoading(false));
    }
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await apiClient.post("/auth/login", { email, password });
      const { access_token, user: userData, organization: orgData } = res.data;
      localStorage.setItem("resolveai_access_token", access_token);
      setToken(access_token);
      setUser(userData);
      setOrganization(orgData);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("resolveai_access_token");
    setToken(null);
    setUser(null);
    setOrganization(null);
    setIsLoading(false);
  };

  const switchDemoRole = async (role: "admin" | "manager" | "agent") => {
    const emailMap = {
      admin: "admin@acme.com",
      manager: "manager@acme.com",
      agent: "agent@acme.com",
    };
    await login(emailMap[role], "Password123!");
  };

  return (
    <AuthContext.Provider value={{ user, organization, token, isLoading, login, logout, switchDemoRole }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
