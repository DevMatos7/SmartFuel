import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { fetchMe, login as apiLogin, logout as apiLogout, type MeResponse } from "../api/auth";
import { getAccessToken, setAccessToken } from "../api/client";

type AuthContextValue = {
  user: MeResponse | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<MeResponse>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null);
      return;
    }
    const me = await fetchMe();
    setUser(me);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        if (getAccessToken()) {
          await refreshUser();
        }
      } catch {
        setAccessToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    const data = await apiLogin(email, password);
    setAccessToken(data.access_token);
    const me = await fetchMe();
    setUser(me);
    return me;
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      setAccessToken(null);
      setUser(null);
      localStorage.removeItem("active_station_id");
    }
  }, []);

  const hasPermission = useCallback(
    (permission: string) => Boolean(user?.permissions.includes(permission)),
    [user],
  );

  const value = useMemo(
    () => ({ user, loading, login, logout, refreshUser, hasPermission }),
    [user, loading, login, logout, refreshUser, hasPermission],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth deve ser usado dentro de AuthProvider");
  return ctx;
}
