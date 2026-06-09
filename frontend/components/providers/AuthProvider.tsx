"use client";

// AuthProvider is a plain passthrough.
// Token injection for API calls is handled by ClerkGuardedLayout (DashboardLayout.tsx)
// which already holds a valid useAuth() context.
export function AuthProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
