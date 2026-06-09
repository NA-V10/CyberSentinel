"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import dynamic from "next/dynamic";

// UserButton requires ClerkProvider — load it only on the client and only
// when Clerk is configured so it never runs during SSR or in dev mode.
const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "";
const isClerkConfigured =
  (clerkKey.startsWith("pk_test_") || clerkKey.startsWith("pk_live_")) &&
  !clerkKey.includes("your_publishable_key") &&
  !clerkKey.includes("your-clerk");

const UserButton = isClerkConfigured
  ? dynamic(() => import("@clerk/nextjs").then((m) => m.UserButton), { ssr: false })
  : () => (
      <div className="w-8 h-8 rounded-full bg-primary/20 border border-primary/40 flex items-center justify-center">
        <span className="text-xs text-primary font-bold">U</span>
      </div>
    );
import {
  Shield,
  LayoutDashboard,
  AlertTriangle,
  Search,
  GitBranch,
  FileText,
  MessageSquare,
  Settings,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
  BarChart2,
  Zap,
  Wrench,
  Brain,
  ScrollText,
  Swords,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  badge?: number;
  group?: string;
}

const navItems: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/executive", label: "Executive View", icon: BarChart2 },
  { href: "/incidents", label: "Incident Analysis", icon: AlertTriangle },
  { href: "/incidents/similar", label: "Similar Incidents", icon: Search },
  { href: "/simulation", label: "Simulation Mode", icon: Zap },
  { href: "/graph", label: "Graph View", icon: GitBranch },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/mcp-tools", label: "MCP Tools", icon: Wrench },
  { href: "/memory", label: "Memory Bank", icon: Brain },
  { href: "/feedback", label: "Feedback", icon: MessageSquare },
  { href: "/audit-logs", label: "Audit Logs", icon: ScrollText },
  { href: "/admin", label: "Admin Settings", icon: Settings },
];

interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export function Sidebar({ isCollapsed, onToggleCollapse }: SidebarProps) {
  const pathname = usePathname();

  return (
    <motion.aside
      animate={{ width: isCollapsed ? 64 : 240 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="hidden md:flex flex-col h-screen bg-card border-r border-border fixed left-0 top-0 z-40 overflow-hidden"
    >
      {/* Logo */}
      <div className="flex items-center h-16 px-4 border-b border-border shrink-0">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="p-1.5 rounded-lg bg-primary/10 border border-primary/20 shrink-0">
            <Shield className="w-5 h-5 text-primary shrink-0" />
          </div>
          <AnimatePresence>
            {!isCollapsed && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.15 }}
                className="overflow-hidden whitespace-nowrap"
              >
                <span className="text-sm font-bold text-foreground">
                  CyberSentinel{" "}
                  <span className="text-primary">AI</span>
                </span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <button
          onClick={onToggleCollapse}
          className="ml-auto p-1 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors shrink-0"
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Nav Items */}
      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isExact = item.href === "/dashboard" || item.href === "/dashboard/executive";
          const isActive = isExact
            ? pathname === item.href
            : pathname === item.href || pathname.startsWith(item.href + "/");

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-2 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 group relative overflow-hidden",
                isActive
                  ? "bg-primary/10 text-primary border border-primary/20"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              )}
              title={isCollapsed ? item.label : undefined}
            >
              {isActive && (
                <motion.div
                  layoutId="activeNav"
                  className="absolute left-0 top-0 bottom-0 w-0.5 bg-primary rounded-full"
                  transition={{ duration: 0.15 }}
                />
              )}
              <item.icon
                className={cn(
                  "w-5 h-5 shrink-0 transition-transform",
                  isActive ? "text-primary" : "group-hover:scale-110"
                )}
              />
              <AnimatePresence>
                {!isCollapsed && (
                  <motion.span
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: "auto" }}
                    exit={{ opacity: 0, width: 0 }}
                    transition={{ duration: 0.15 }}
                    className="overflow-hidden whitespace-nowrap flex-1"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
              {!isCollapsed && item.badge && (
                <span className="ml-auto px-1.5 py-0.5 text-xs rounded-full bg-destructive/20 text-destructive font-medium">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* User Profile */}
      <div className="p-4 border-t border-border shrink-0">
        <div className={cn("flex items-center gap-3", isCollapsed && "justify-center")}>
          <UserButton
            appearance={{
              elements: {
                avatarBox: "w-8 h-8",
                userButtonPopoverCard: "bg-card border border-border",
                userButtonPopoverActionButton: "text-foreground hover:bg-muted",
                userButtonPopoverActionButtonText: "text-foreground",
                userButtonPopoverFooter: "hidden",
              },
            }}
          />
          <AnimatePresence>
            {!isCollapsed && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.15 }}
                className="overflow-hidden whitespace-nowrap"
              >
                <p className="text-xs text-muted-foreground">Account</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.aside>
  );
}

export function MobileSidebar() {
  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname();

  return (
    <>
      {/* Mobile toggle button */}
      <button
        onClick={() => setIsOpen(true)}
        className="md:hidden fixed top-4 left-4 z-50 p-2 rounded-lg bg-card border border-border text-muted-foreground hover:text-foreground transition-colors"
        aria-label="Open menu"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Overlay */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsOpen(false)}
            className="md:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
          />
        )}
      </AnimatePresence>

      {/* Mobile sidebar */}
      <AnimatePresence>
        {isOpen && (
          <motion.aside
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            exit={{ x: -280 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="md:hidden fixed left-0 top-0 bottom-0 w-64 bg-card border-r border-border z-50 flex flex-col"
          >
            {/* Mobile logo */}
            <div className="flex items-center justify-between h-16 px-4 border-b border-border">
              <div className="flex items-center gap-2">
                <Shield className="w-6 h-6 text-primary" />
                <span className="text-sm font-bold text-foreground">
                  CyberSentinel <span className="text-primary">AI</span>
                </span>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 rounded-md hover:bg-muted text-muted-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Mobile nav */}
            <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
              {navItems.map((item) => {
                const isExactMobile = item.href === "/dashboard" || item.href === "/dashboard/executive";
                const isActive = isExactMobile
                  ? pathname === item.href
                  : pathname === item.href || pathname.startsWith(item.href + "/");

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setIsOpen(false)}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                      isActive
                        ? "bg-primary/10 text-primary border border-primary/20"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted"
                    )}
                  >
                    <item.icon className="w-5 h-5 shrink-0" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>

            <div className="p-4 border-t border-border">
              <div className="flex items-center gap-3">
                <UserButton />
                <span className="text-xs text-muted-foreground">Account</span>
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  );
}
