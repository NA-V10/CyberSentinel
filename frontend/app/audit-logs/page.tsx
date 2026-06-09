"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  ScrollText, RefreshCw, Filter, ChevronDown, ChevronLeft,
  ChevronRight, Shield, User, Wrench, AlertTriangle, CheckCircle2,
  Clock, Info
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import api from "@/lib/api";

interface AuditLogItem {
  id: string;
  user_id: string;
  event_type: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  org_id: string | null;
  created_at: string;
}

const EVENT_TYPE_CONFIG: Record<string, { color: string; icon: React.ElementType; label: string }> = {
  incident_analyzed: { color: "text-blue-400", icon: Shield, label: "Incident Analyzed" },
  incident_approved: { color: "text-green-400", icon: CheckCircle2, label: "Approved" },
  incident_rejected: { color: "text-red-400", icon: AlertTriangle, label: "Rejected" },
  incident_escalated: { color: "text-orange-400", icon: AlertTriangle, label: "Escalated" },
  feedback_submitted: { color: "text-purple-400", icon: User, label: "Feedback" },
  memory_stored: { color: "text-primary", icon: Wrench, label: "Memory Stored" },
  playbook_generated: { color: "text-amber-400", icon: Wrench, label: "Playbook Generated" },
  sla_assigned: { color: "text-yellow-400", icon: Clock, label: "SLA Assigned" },
  sla_breached: { color: "text-red-500", icon: AlertTriangle, label: "SLA Breached" },
  login: { color: "text-teal-400", icon: User, label: "Login" },
};

const FALLBACK_LOGS: AuditLogItem[] = [
  { id: "a1", user_id: "user_analyst01", event_type: "incident_analyzed", resource_type: "incident", resource_id: "inc-001", details: { attack_type: "Brute Force", severity: "high", risk_score: 78 }, ip_address: "192.168.1.10", org_id: "org_demo", created_at: "2024-01-15T15:23:00Z" },
  { id: "a2", user_id: "user_analyst01", event_type: "incident_approved", resource_type: "incident", resource_id: "inc-001", details: { reason: "Mitigation steps validated", auto_approved: false }, ip_address: "192.168.1.10", org_id: "org_demo", created_at: "2024-01-15T15:30:00Z" },
  { id: "a3", user_id: "user_analyst02", event_type: "incident_escalated", resource_type: "incident", resource_id: "inc-002", details: { escalated_to: "L3 Specialist", reason: "APT indicators detected" }, ip_address: "192.168.1.15", org_id: "org_demo", created_at: "2024-01-15T14:45:00Z" },
  { id: "a4", user_id: "user_soc_lead", event_type: "playbook_generated", resource_type: "incident", resource_id: "inc-003", details: { attack_type: "Phishing", steps_count: 18 }, ip_address: "192.168.1.5", org_id: "org_demo", created_at: "2024-01-15T14:00:00Z" },
  { id: "a5", user_id: "user_analyst01", event_type: "feedback_submitted", resource_type: "incident", resource_id: "inc-001", details: { rating: 5, mitigation_worked: true }, ip_address: "192.168.1.10", org_id: "org_demo", created_at: "2024-01-15T15:45:00Z" },
  { id: "a6", user_id: "user_analyst03", event_type: "sla_breached", resource_type: "incident", resource_id: "inc-004", details: { severity: "critical", sla_minutes: 15, elapsed_minutes: 22 }, ip_address: "192.168.1.20", org_id: "org_demo", created_at: "2024-01-15T13:30:00Z" },
  { id: "a7", user_id: "user_analyst02", event_type: "memory_stored", resource_type: "memory", resource_id: "mem-001", details: { scope: "incident", key: "brute_force_pattern" }, ip_address: "192.168.1.15", org_id: "org_demo", created_at: "2024-01-15T13:15:00Z" },
  { id: "a8", user_id: "user_soc_lead", event_type: "incident_rejected", resource_type: "incident", resource_id: "inc-005", details: { reason: "False positive — dev environment scan" }, ip_address: "192.168.1.5", org_id: "org_demo", created_at: "2024-01-15T12:50:00Z" },
];

const PAGE_SIZE = 20;

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  const loadLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      };
      if (eventTypeFilter) params.event_type = eventTypeFilter;
      const res = await api.get("/audit-logs/", { params });
      setLogs(res.data.items || []);
      setTotal(res.data.total || res.data.items?.length || 0);
    } catch {
      setLogs(FALLBACK_LOGS);
      setTotal(FALLBACK_LOGS.length);
    } finally {
      setLoading(false);
    }
  }, [page, eventTypeFilter]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const getEventConfig = (eventType: string) => {
    return EVENT_TYPE_CONFIG[eventType] || { color: "text-muted-foreground", icon: Info, label: eventType };
  };

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
              <ScrollText className="w-6 h-6 text-primary" />
            </div>
            Audit Logs
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Immutable action trail — all analyst activity and automated events
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-3 py-2 rounded-md border text-sm font-medium transition-colors ${
              showFilters ? "bg-primary/10 text-primary border-primary/30" : "border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            <Filter className="w-4 h-4" />
            Filter
          </button>
          <button onClick={loadLogs} className="p-2 border border-border rounded-md text-muted-foreground hover:text-foreground transition-colors">
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          className="cyber-card p-4 border border-border mb-6"
        >
          <div className="flex items-center gap-3 flex-wrap">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Event Type</label>
              <select
                value={eventTypeFilter}
                onChange={e => { setEventTypeFilter(e.target.value); setPage(0); }}
                className="cyber-input text-sm py-1.5 pr-8 min-w-[180px]"
              >
                <option value="">All Events</option>
                {Object.entries(EVENT_TYPE_CONFIG).map(([key, { label }]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
            {eventTypeFilter && (
              <button
                onClick={() => { setEventTypeFilter(""); setPage(0); }}
                className="text-xs text-muted-foreground hover:text-foreground mt-5"
              >
                Clear filters
              </button>
            )}
          </div>
        </motion.div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {Object.entries({
          "Total Events": total,
          "Approvals": logs.filter(l => l.event_type === "incident_approved").length,
          "Escalations": logs.filter(l => l.event_type === "incident_escalated").length,
          "SLA Breaches": logs.filter(l => l.event_type === "sla_breached").length,
        }).map(([label, count], i) => (
          <motion.div
            key={label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="cyber-card p-3 border border-border text-center"
          >
            <div className="text-lg font-bold text-foreground">{count}</div>
            <div className="text-xs text-muted-foreground">{label}</div>
          </motion.div>
        ))}
      </div>

      {/* Log table */}
      <div className="cyber-card border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left p-3 text-xs font-semibold text-muted-foreground">Time</th>
                <th className="text-left p-3 text-xs font-semibold text-muted-foreground">Event</th>
                <th className="text-left p-3 text-xs font-semibold text-muted-foreground">User</th>
                <th className="text-left p-3 text-xs font-semibold text-muted-foreground">Resource</th>
                <th className="text-left p-3 text-xs font-semibold text-muted-foreground">IP</th>
                <th className="text-left p-3 text-xs font-semibold text-muted-foreground">Details</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="border-b border-border/50">
                    <td colSpan={6} className="p-3">
                      <div className="h-4 bg-muted/50 rounded animate-pulse" />
                    </td>
                  </tr>
                ))
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-muted-foreground">
                    No audit logs found.
                  </td>
                </tr>
              ) : (
                logs.map((log, i) => {
                  const cfg = getEventConfig(log.event_type);
                  const Icon = cfg.icon;
                  const isExpanded = expandedId === log.id;
                  return (
                    <>
                      <motion.tr
                        key={log.id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: i * 0.02 }}
                        className="border-b border-border/50 hover:bg-muted/20 transition-colors cursor-pointer"
                        onClick={() => setExpandedId(isExpanded ? null : log.id)}
                      >
                        <td className="p-3 text-xs text-muted-foreground whitespace-nowrap">
                          <div>{new Date(log.created_at).toLocaleDateString()}</div>
                          <div className="text-[10px]">{new Date(log.created_at).toLocaleTimeString()}</div>
                        </td>
                        <td className="p-3">
                          <div className={`flex items-center gap-1.5 font-medium ${cfg.color}`}>
                            <Icon className="w-3.5 h-3.5 shrink-0" />
                            <span className="text-xs">{cfg.label}</span>
                          </div>
                        </td>
                        <td className="p-3 text-xs font-mono text-foreground">{log.user_id}</td>
                        <td className="p-3 text-xs text-muted-foreground">
                          {log.resource_type && (
                            <span>{log.resource_type}</span>
                          )}
                          {log.resource_id && (
                            <div className="font-mono text-[10px] text-muted-foreground/70 truncate max-w-[100px]">
                              {log.resource_id}
                            </div>
                          )}
                        </td>
                        <td className="p-3 text-xs font-mono text-muted-foreground">{log.ip_address || "—"}</td>
                        <td className="p-3">
                          <ChevronDown className={`w-3.5 h-3.5 text-muted-foreground transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                        </td>
                      </motion.tr>
                      {isExpanded && (
                        <tr key={`${log.id}-details`} className="border-b border-border/50 bg-muted/10">
                          <td colSpan={6} className="px-6 py-3">
                            <pre className="text-xs text-foreground font-mono bg-muted/30 border border-border rounded p-3 overflow-auto max-h-32 whitespace-pre-wrap">
                              {JSON.stringify(log.details, null, 2)}
                            </pre>
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border">
            <span className="text-xs text-muted-foreground">
              Page {page + 1} of {totalPages} ({total} total)
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="p-1.5 rounded border border-border text-muted-foreground hover:text-foreground disabled:opacity-40 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="p-1.5 rounded border border-border text-muted-foreground hover:text-foreground disabled:opacity-40 transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
