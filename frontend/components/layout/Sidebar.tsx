"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import dynamic from "next/dynamic";
import {
  Shield, LayoutDashboard, AlertTriangle, Search, GitBranch,
  FileText, MessageSquare, Settings, ChevronLeft, ChevronRight,
  Menu, X, BarChart2, Zap, Wrench, Brain, ScrollText, Swords,
} from "lucide-react";
import { cn } from "@/lib/utils";

const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "";
const isClerkConfigured =
  (clerkKey.startsWith("pk_test_") || clerkKey.startsWith("pk_live_")) &&
  !clerkKey.includes("your_publishable_key") &&
  !clerkKey.includes("your-clerk");

const UserButton = isClerkConfigured
  ? dynamic(() => import("@clerk/nextjs").then((m) => m.UserButton), { ssr: false })
  : () => (
      <div className="w-7 h-7 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center">
        <span className="text-xs text-primary font-bold">U</span>
      </div>
    );

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  badge?: number;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/dashboard/executive", label: "Executive View", icon: BarChart2 },
    ],
  },
  {
    label: "Investigations",
    items: [
      { href: "/incidents", label: "Incident Analysis", icon: AlertTriangle },
      { href: "/incidents/similar", label: "Similar Incidents", icon: Search },
      { href: "/simulation", label: "Simulation Mode", icon: Zap },
      { href: "/graph", label: "Knowledge Graph", icon: GitBranch },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { href: "/reports", label: "Reports", icon: FileText },
      { href: "/mcp-tools", label: "MCP Tools", icon: Wrench },
      { href: "/memory", label: "Memory Bank", icon: Brain },
    ],
  },
  {
    label: "System",
    items: [
      { href: "/feedback", label: "Feedback", icon: MessageSquare },
      { href: "/audit-logs", label: "Audit Logs", icon: ScrollText },
      { href: "/admin", label: "Admin Settings", icon: Settings },
    ],
  },
];

const allNavItems = navGroups.flatMap((g) => g.items);

function isActive(pathname: string, href: string) {
  const exactMatch = href === "/dashboard" || href === "/dashboard/executive";
  return exactMatch
    ? pathname === href
    : pathname === href || pathname.startsWith(href + "/");
}

/* ── Collapsed tooltip ────────────────────────────────────────────────────── */
function NavTooltip({ label }: { label: string }) {
  return (
    <div className="absolute left-full ml-3 px-2.5 py-1.5 rounded-md bg-popover border border-border text-xs font-medium text-foreground whitespace-nowrap shadow-xl pointer-events-none z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
      {label}
      <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-border" />
    </div>
  );
}

/* ── Desktop Sidebar ──────────────────────────────────────────────────────── */
interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export function Sidebar({ isCollapsed, onToggleCollapse }: SidebarProps) {
  const pathname = usePathname();

  return (
    <motion.aside
      animate={{ width: isCollapsed ? 60 : 236 }}
      transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
      className="hidden md:flex flex-col h-screen bg-card/80 border-r border-border fixed left-0 top-0 z-40 overflow-hidden"
      style={{ backdropFilter: "blur(12px)" }}
    >
      {/* Logo row */}
      <div className="flex items-center h-14 px-3 border-b border-border shrink-0">
        <div className="flex items-center gap-2.5 overflow-hidden flex-1 min-w-0">
          <div className="p-1.5 rounded-lg bg-primary/10 border border-primary/20 shrink-0 relative">
            <Shield className="w-4 h-4 text-primary" />
            <span className="absolute top-0.5 right-0.5 w-1.5 h-1.5 rounded-full bg-accent status-online" />
          </div>
          <AnimatePresence>
            {!isCollapsed && (
              <motion.div
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={{ duration: 0.18 }}
                className="overflow-hidden whitespace-nowrap"
              >
                <span className="text-sm font-bold tracking-tight text-foreground">
                  Cyber<span className="text-primary">Sentinel</span>
                </span>
                <div className="text-[9px] text-muted-foreground font-medium tracking-widest uppercase">
                  AI Command Center
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <button
          type="button"
          onClick={onToggleCollapse}
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="ml-auto p-1 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors shrink-0"
        >
          {isCollapsed
            ? <ChevronRight className="w-3.5 h-3.5" />
            : <ChevronLeft className="w-3.5 h-3.5" />
          }
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 px-2 overflow-y-auto space-y-0.5 scrollbar-none">
        {navGroups.map((group) => (
          <div key={group.label} className="mb-1">
            {/* Group label */}
            <AnimatePresence>
              {!isCollapsed && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.15 }}
                  className="px-2 py-1.5 text-[10px] font-semibold tracking-widest uppercase text-muted-foreground/60 select-none"
                >
                  {group.label}
                </motion.div>
              )}
            </AnimatePresence>
            {isCollapsed && <div className="border-t border-border/50 my-1.5 mx-1" />}

            {group.items.map((item) => {
              const active = isActive(pathname, item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "relative flex items-center gap-2.5 px-2 py-2 rounded-lg text-sm font-medium transition-all duration-150 group overflow-visible",
                    active
                      ? "bg-primary/8 text-primary"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
                  )}
                  title={undefined}
                >
                  {/* Active left bar */}
                  {active && (
                    <motion.span
                      layoutId="sidebarActive"
                      className="nav-active-line"
                      transition={{ type: "spring", stiffness: 380, damping: 34 }}
                    />
                  )}

                  <item.icon
                    className={cn(
                      "w-4 h-4 shrink-0 transition-transform duration-150",
                      active ? "text-primary" : "group-hover:scale-110"
                    )}
                  />

                  <AnimatePresence>
                    {!isCollapsed && (
                      <motion.span
                        initial={{ opacity: 0, width: 0 }}
                        animate={{ opacity: 1, width: "auto" }}
                        exit={{ opacity: 0, width: 0 }}
                        transition={{ duration: 0.16 }}
                        className="overflow-hidden whitespace-nowrap flex-1 text-[13px]"
                      >
                        {item.label}
                      </motion.span>
                    )}
                  </AnimatePresence>

                  {/* Badge */}
                  {!isCollapsed && item.badge && (
                    <span className="ml-auto px-1.5 py-0.5 text-[10px] rounded-full bg-destructive/20 text-destructive font-semibold">
                      {item.badge}
                    </span>
                  )}

                  {/* Tooltip when collapsed */}
                  {isCollapsed && <NavTooltip label={item.label} />}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* User row */}
      <div className="p-3 border-t border-border shrink-0">
        <div className={cn("flex items-center gap-2.5", isCollapsed && "justify-center")}>
          <UserButton
            appearance={{
              elements: {
                avatarBox: "w-7 h-7",
                userButtonPopoverCard: "bg-card border border-border shadow-xl",
                userButtonPopoverActionButton: "text-foreground hover:bg-muted",
                userButtonPopoverActionButtonText: "text-foreground",
                userButtonPopoverFooter: "hidden",
              },
            }}
          />
          <AnimatePresence>
            {!isCollapsed && (
              <motion.div
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={{ duration: 0.15 }}
                className="overflow-hidden whitespace-nowrap"
              >
                <p className="text-[11px] font-medium text-foreground">Account</p>
                <p className="text-[10px] text-muted-foreground">SOC Analyst</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.aside>
  );
}

/* ── Mobile Sidebar ───────────────────────────────────────────────────────── */
export function MobileSidebar() {
  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname();

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        aria-label="Open navigation menu"
        className="md:hidden fixed top-3.5 left-3.5 z-50 p-2 rounded-lg bg-card border border-border text-muted-foreground hover:text-foreground transition-colors shadow-lg"
      >
        <Menu className="w-4 h-4" />
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="md:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
            />
            <motion.aside
              initial={{ x: -260 }}
              animate={{ x: 0 }}
              exit={{ x: -260 }}
              transition={{ type: "spring", damping: 28, stiffness: 240 }}
              className="md:hidden fixed left-0 top-0 bottom-0 w-60 bg-card border-r border-border z-50 flex flex-col shadow-2xl"
            >
              {/* Mobile logo */}
              <div className="flex items-center justify-between h-14 px-4 border-b border-border">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-primary/10 border border-primary/20">
                    <Shield className="w-4 h-4 text-primary" />
                  </div>
                  <span className="text-sm font-bold text-foreground">
                    Cyber<span className="text-primary">Sentinel</span>
                  </span>
                </div>
                <button type="button" onClick={() => setIsOpen(false)} aria-label="Close navigation menu" className="p-1 rounded-md hover:bg-muted text-muted-foreground">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Mobile nav */}
              <nav className="flex-1 py-3 px-2 overflow-y-auto space-y-0.5">
                {navGroups.map((group) => (
                  <div key={group.label} className="mb-1">
                    <div className="px-2 py-1.5 text-[10px] font-semibold tracking-widest uppercase text-muted-foreground/60">
                      {group.label}
                    </div>
                    {group.items.map((item) => {
                      const active = isActive(pathname, item.href);
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          onClick={() => setIsOpen(false)}
                          className={cn(
                            "relative flex items-center gap-2.5 px-2 py-2 rounded-lg text-[13px] font-medium transition-colors",
                            active
                              ? "bg-primary/8 text-primary"
                              : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
                          )}
                        >
                          {active && <span className="nav-active-line" />}
                          <item.icon className="w-4 h-4 shrink-0" />
                          {item.label}
                        </Link>
                      );
                    })}
                  </div>
                ))}
              </nav>

              <div className="p-3 border-t border-border">
                <div className="flex items-center gap-2.5">
                  <UserButton />
                  <div>
                    <p className="text-[11px] font-medium text-foreground">Account</p>
                    <p className="text-[10px] text-muted-foreground">SOC Analyst</p>
                  </div>
                </div>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
