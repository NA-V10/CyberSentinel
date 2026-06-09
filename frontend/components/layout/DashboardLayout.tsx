"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { redirect } from "next/navigation";
import { Sidebar, MobileSidebar } from "./Sidebar";
import { setTokenGetter } from "@/lib/api";
import { cn } from "@/lib/utils";

const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "";
const isClerkConfigured =
  (clerkKey.startsWith("pk_test_") || clerkKey.startsWith("pk_live_")) &&
  !clerkKey.includes("your_publishable_key") &&
  !clerkKey.includes("your-clerk");

// ── Shell ────────────────────────────────────────────────────────────────────
// Pure layout: sidebar + main content area. No Clerk dependency.

function Shell({ children }: { children: React.ReactNode }) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  return (
    <div className="min-h-screen bg-background">
      <Sidebar
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
      />
      <MobileSidebar />
      <main
        className={cn(
          "transition-all duration-200 min-h-screen",
          isCollapsed ? "md:pl-16" : "md:pl-60"
        )}
      >
        <div className="p-4 md:p-6 lg:p-8">{children}</div>
      </main>
    </div>
  );
}

// ── ClerkGuardedLayout ───────────────────────────────────────────────────────
// Only rendered when ClerkProvider is guaranteed to be in the tree.
// useAuth() is called unconditionally at the top level — rules-of-hooks OK.

function ClerkGuardedLayout({ children }: { children: React.ReactNode }) {
  const { isLoaded, userId, getToken } = useAuth();

  // Inject Clerk JWT into every axios request once session is ready
  useEffect(() => {
    if (isLoaded && userId) {
      setTokenGetter(() => getToken());
    }
  }, [isLoaded, userId, getToken]);

  if (isLoaded && !userId) {
    redirect("/sign-in");
  }

  return <Shell>{children}</Shell>;
}

// ── DevLayout ────────────────────────────────────────────────────────────────
// Used when Clerk keys are not configured (local dev / demo mode).

function DevLayout({ children }: { children: React.ReactNode }) {
  return <Shell>{children}</Shell>;
}

// ── DashboardLayout (export) ─────────────────────────────────────────────────

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  if (isClerkConfigured) {
    return <ClerkGuardedLayout>{children}</ClerkGuardedLayout>;
  }
  return <DevLayout>{children}</DevLayout>;
}
