"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { redirect, usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Sidebar, MobileSidebar } from "./Sidebar";
import { setTokenGetter } from "@/lib/api";
import { cn } from "@/lib/utils";

const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "";
const isClerkConfigured =
  (clerkKey.startsWith("pk_test_") || clerkKey.startsWith("pk_live_")) &&
  !clerkKey.includes("your_publishable_key") &&
  !clerkKey.includes("your-clerk");

/* ── Page transition wrapper ─────────────────────────────────────────────── */
function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={pathname}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -6 }}
        transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}

/* ── Shell ───────────────────────────────────────────────────────────────── */
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
          "transition-[padding] duration-[220ms] ease-[cubic-bezier(0.4,0,0.2,1)] min-h-screen",
          isCollapsed ? "md:pl-[60px]" : "md:pl-[236px]"
        )}
      >
        {/* Subtle top border line */}
        <div className="h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent" />
        <div className="p-4 md:p-6 lg:p-8 max-w-[1600px] mx-auto">
          <PageTransition>{children}</PageTransition>
        </div>
      </main>
    </div>
  );
}

/* ── ClerkGuardedLayout ──────────────────────────────────────────────────── */
function ClerkGuardedLayout({ children }: { children: React.ReactNode }) {
  const { isLoaded, userId, getToken } = useAuth();

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

/* ── DevLayout ───────────────────────────────────────────────────────────── */
function DevLayout({ children }: { children: React.ReactNode }) {
  return <Shell>{children}</Shell>;
}

/* ── Export ──────────────────────────────────────────────────────────────── */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  if (isClerkConfigured) {
    return <ClerkGuardedLayout>{children}</ClerkGuardedLayout>;
  }
  return <DevLayout>{children}</DevLayout>;
}
