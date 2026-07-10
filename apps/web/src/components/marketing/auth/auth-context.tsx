"use client";

import * as React from "react";

/**
 * Mock authentication for the marketing site.
 *
 * This is intentionally a CLIENT-SIDE STUB — it stores a fake user in
 * localStorage and gates nothing. Access to /dashboard and /workspace stays
 * fully open (testing mode). The real Google OAuth (PKCE) flow specced in
 * docs/architecture/auth-strategy.md slots in here later: `signIn` would kick
 * off the authorization-code redirect, and the resolved profile would replace
 * the mock user — the rest of the UI (nav, user menu) needs no changes.
 */

export interface MockUser {
  name: string;
  email: string;
  avatarUrl?: string;
}

interface AuthContextValue {
  user: MockUser | null;
  signIn: () => void;
  signOut: () => void;
}

const STORAGE_KEY = "scotch-mock-user";

// Stand-in identity used until real OAuth lands.
const DEMO_USER: MockUser = {
  name: "Demo Architect",
  email: "demo@scotch.studio",
};

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<MockUser | null>(null);

  React.useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) setUser(JSON.parse(raw) as MockUser);
    } catch {
      /* ignore corrupt/unavailable storage */
    }
  }, []);

  const signIn = React.useCallback(() => {
    // Real flow (later): begin Google PKCE redirect instead of setting a mock.
    setUser(DEMO_USER);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(DEMO_USER));
    } catch {
      /* ignore */
    }
  }, []);

  const signOut = React.useCallback(() => {
    setUser(null);
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const value = React.useMemo(
    () => ({ user, signIn, signOut }),
    [user, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
