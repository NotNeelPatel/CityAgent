import { type User } from "@supabase/supabase-js";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { supabase } from "@/lib/client";

type AppRole = "general" | "employee" | "admin";

interface AuthContextType {
  user: User | null;
  role: AppRole | null;
  loading: boolean;
  signInWithGoogle: () => void;
  signInWithAzure: () => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [role, setRole] = useState<AppRole | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setRole(getRoleFromAccessToken(session?.access_token));
      setLoading(false);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      setRole(getRoleFromAccessToken(session?.access_token));
      setLoading(false);
    });

    return () => {
      listener.subscription.unsubscribe();
    };
  }, []);

  const signInWithGoogle = async () => {
    supabase.auth.signInWithOAuth({ provider: "google" });
  }

  const signInWithAzure = async () => {
    supabase.auth.signInWithOAuth({ provider: "azure" });
  }

  const signOut = async () => {
    await supabase.auth.signOut();
    await supabase.auth.refreshSession();
  };

  const contextValue = useMemo(
    () => ({
      user,
      role,
      loading,
      signInWithGoogle,
      signInWithAzure,
      signOut,
    }),
    [user, role, loading]
  );


  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>

  );
};


export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) throw new Error("useAuth must be used within an AuthProvider");
  return context;
};

function decodeJwtPayload(token: string): any {
  const base64Url = token.split(".")[1];
  const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
  const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
  const json = decodeURIComponent(
    atob(padded)
      .split("")
      .map((c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0"))
      .join("")
  );
  return JSON.parse(json);
}

function getRoleFromAccessToken(accessToken?: string): AppRole | null {
  if (!accessToken) return null;
  try {
    const payload = decodeJwtPayload(accessToken);
    const role = payload?.user_role as AppRole | undefined;
    return role === "general" || role === "employee" || role === "admin" ? role : null;
  } catch {
    return null;
  }
}
