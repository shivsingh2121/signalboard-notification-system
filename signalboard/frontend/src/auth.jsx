import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, tokenStore } from "./api.js";
import { logoutPush } from "./push.js";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(tokenStore.get()));

  const refresh = useCallback(async () => {
    if (!tokenStore.get()) {
      setUser(null);
      setLoading(false);
      return null;
    }
    try {
      const me = await api("/api/auth/me/");
      setUser(me);
      return me;
    } catch {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = async (email, password) => {
    const res = await api("/api/auth/login/", { method: "POST", body: { email, password } });
    tokenStore.set(res.token);
    setUser(res.user);
    return res.user;
  };

  const register = async (payload) => {
    const res = await api("/api/auth/register/", { method: "POST", body: payload });
    tokenStore.set(res.token);
    setUser(res.user);
    return res.user;
  };

  const logout = async () => {
    try {
      await api("/api/auth/logout/", { method: "POST" });
    } finally {
      tokenStore.clear();
      setUser(null);
      logoutPush();
    }
  };

  return (
    <AuthCtx.Provider value={{ user, setUser, loading, login, register, logout, refresh }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
