"use client";

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  AreaChart, Area, PieChart, Pie, Cell, BarChart, Bar, Sector,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  Shield, AlertTriangle, Clock, Activity, TrendingUp, TrendingDown,
  ArrowRight, RefreshCw, Zap, ChevronRight,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { SeverityBadge } from "@/components/incidents/SeverityBadge";
import { formatRelativeTime } from "@/lib/utils";

/* ── Palette ─────────────────────────────────────────────────────────────── */
const COLORS = {
  cyan:   "#00d4ff",
  green:  "#10b981",
  red:    "#ef4444",
  orange: "#f97316",
  amber:  "#f59e0b",
  violet: "#7c3aed",
  slate:  "#475569",
};

/* ── Data ────────────────────────────────────────────────────────────────── */
const incidentTrendData = [
  { date: "Jun 1",  incidents: 12, resolved: 10 },
  { date: "Jun 2",  incidents: 19, resolved: 15 },
  { date: "Jun 3",  incidents: 8,  resolved: 8  },
  { date: "Jun 4",  incidents: 25, resolved: 18 },
  { date: "Jun 5",  incidents: 17, resolved: 14 },
  { date: "Jun 6",  incidents: 22, resolved: 20 },
  { date: "Jun 7",  incidents: 14, resolved: 12 },
];

const attackTypeData = [
  { name: "Ransomware",    value: 28, color: COLORS.red,    textClass: "text-red-400",    dotClass: "bg-red-500"    },
  { name: "Phishing",      value: 22, color: COLORS.orange, textClass: "text-orange-400", dotClass: "bg-orange-500" },
  { name: "DDoS",          value: 18, color: COLORS.amber,  textClass: "text-amber-400",  dotClass: "bg-amber-500"  },
  { name: "SQL Injection", value: 15, color: COLORS.violet, textClass: "text-violet-400", dotClass: "bg-violet-600" },
  { name: "Zero-Day",      value: 10, color: COLORS.cyan,   textClass: "text-primary",    dotClass: "bg-cyan-400"   },
  { name: "Other",         value:  7, color: COLORS.slate,  textClass: "text-slate-400",  dotClass: "bg-slate-500"  },
];

const severityData = [
  { severity: "Critical", count:  8, fill: COLORS.red,    gradId: "d-sev-crit" },
  { severity: "High",     count: 23, fill: COLORS.orange, gradId: "d-sev-high" },
  { severity: "Medium",   count: 45, fill: COLORS.amber,  gradId: "d-sev-med"  },
  { severity: "Low",      count: 67, fill: COLORS.green,  gradId: "d-sev-low"  },
];

const recentIncidents = [
  { id: "INC-001", description: "Ransomware detected on finance servers — encrypted 200 files", severity: "critical", threat_class: "Ransomware",    created_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),     status: "active"    },
  { id: "INC-002", description: "Suspicious SSH brute force from IP 192.168.1.45",             severity: "high",     threat_class: "Brute Force",   created_at: new Date(Date.now() - 45 * 60 * 1000).toISOString(),     status: "analyzing" },
  { id: "INC-003", description: "SQL injection attempt on customer portal API endpoint",        severity: "medium",   threat_class: "SQL Injection", created_at: new Date(Date.now() - 2 * 3600 * 1000).toISOString(),   status: "resolved"  },
  { id: "INC-004", description: "Phishing email campaign targeting HR department",              severity: "high",     threat_class: "Phishing",      created_at: new Date(Date.now() - 3 * 3600 * 1000).toISOString(),   status: "resolved"  },
  { id: "INC-005", description: "DDoS attack on public API — 50K requests/sec",               severity: "critical", threat_class: "DDoS",          created_at: new Date(Date.now() - 5 * 3600 * 1000).toISOString(),   status: "resolved"  },
];

const stats = [
  { label: "Total Incidents",   value: "143", trend: "+12%", trendUp: true,  icon: Shield,        color: "text-primary",    bg: "bg-primary/10",    border: "border-primary/20",    accentBar: "bg-primary",    glowClass: "bg-primary/15"    },
  { label: "Critical Alerts",   value: "8",   trend: "-3%",  trendUp: false, icon: AlertTriangle, color: "text-red-400",    bg: "bg-red-500/10",    border: "border-red-500/20",    accentBar: "bg-red-400",    glowClass: "bg-red-500/15"    },
  { label: "Avg Response Time", value: "1.8s",trend: "-0.4s",trendUp: false, icon: Clock,         color: "text-green-400",  bg: "bg-green-500/10",  border: "border-green-500/20",  accentBar: "bg-green-400",  glowClass: "bg-green-500/15"  },
  { label: "Active Sessions",   value: "24",  trend: "+5",   trendUp: true,  icon: Activity,      color: "text-purple-400", bg: "bg-purple-500/10", border: "border-purple-500/20", accentBar: "bg-purple-500", glowClass: "bg-purple-500/15" },
];

/* ── Tooltip ─────────────────────────────────────────────────────────────── */
const SERIES_DOT: Record<string, string> = {
  "Total Incidents": "bg-primary",
  "Resolved":        "bg-green-400",
  "Count":           "bg-slate-400",
};

function ChartTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: Array<{ name: string; value: number }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-card px-3 py-2.5 text-xs shadow-2xl">
      <p className="text-muted-foreground mb-1.5 font-medium">{label}</p>
      {payload.map((e, i) => (
        <div key={i} className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full shrink-0 ${SERIES_DOT[e.name] ?? "bg-muted-foreground"}`} />
          <span className="text-foreground">{e.name}: <strong>{e.value}</strong></span>
        </div>
      ))}
    </div>
  );
}

/* ── Active-shape donut ──────────────────────────────────────────────────── */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const renderActiveShape = (props: any) => {
  const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill, payload, value, percent } = props;
  return (
    <g>
      {/* Center label */}
      <text x={cx} y={cy - 8} textAnchor="middle" fill="#e2e8f0" fontSize={20} fontWeight={700}>
        {value}
      </text>
      <text x={cx} y={cy + 12} textAnchor="middle" fill="#64748b" fontSize={10} fontWeight={500}>
        {payload.name}
      </text>
      <text x={cx} y={cy + 26} textAnchor="middle" fill={fill} fontSize={11} fontWeight={600}>
        {(percent * 100).toFixed(0)}%
      </text>

      {/* Expanded outer ring */}
      <Sector cx={cx} cy={cy} innerRadius={innerRadius} outerRadius={outerRadius + 8}
        startAngle={startAngle} endAngle={endAngle} fill={fill} opacity={0.95} />

      {/* Outer glow ring */}
      <Sector cx={cx} cy={cy} innerRadius={outerRadius + 10} outerRadius={outerRadius + 14}
        startAngle={startAngle} endAngle={endAngle} fill={fill} opacity={0.3} />
    </g>
  );
};

/* ── Default donut center label ──────────────────────────────────────────── */
function DonutCenter({ cx = 0, cy = 0, total }: { cx?: number; cy?: number; total: number }) {
  return (
    <g>
      <text x={cx} y={cy - 6} textAnchor="middle" fill="#e2e8f0" fontSize={22} fontWeight={700}>{total}</text>
      <text x={cx} y={cy + 12} textAnchor="middle" fill="#64748b" fontSize={10}>incidents</text>
    </g>
  );
}

/* ── Status pill ─────────────────────────────────────────────────────────── */
function StatusPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    active:    "bg-red-500/10 text-red-400 border-red-500/25",
    analyzing: "bg-primary/10 text-primary border-primary/25",
    resolved:  "bg-green-500/10 text-green-400 border-green-500/25",
  };
  return (
    <span className={`text-[11px] px-2 py-0.5 rounded-full border font-medium ${map[status] ?? "bg-muted text-muted-foreground border-border"}`}>
      {status === "active" && <span className="mr-1">●</span>}
      {status}
    </span>
  );
}

/* ── Stagger variants ────────────────────────────────────────────────────── */
const stagger = {
  container: { hidden: {}, show: { transition: { staggerChildren: 0.07 } } },
  item:      { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.4, 0, 0.2, 1] } } },
};

/* ── Page ────────────────────────────────────────────────────────────────── */
export default function DashboardPage() {
  const router = useRouter();
  const [quickAnalysis, setQuickAnalysis] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activeIndex, setActiveIndex] = useState<number | undefined>(undefined);

  const onPieEnter = useCallback((_: unknown, index: number) => setActiveIndex(index), []);
  const onPieLeave = useCallback(() => setActiveIndex(undefined), []);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await new Promise(r => setTimeout(r, 900));
    setIsRefreshing(false);
  };

  const handleQuickAnalysis = () => {
    if (quickAnalysis.trim()) router.push(`/incidents?description=${encodeURIComponent(quickAnalysis)}`);
  };

  const total = attackTypeData.reduce((s, d) => s + d.value, 0);

  return (
    <DashboardLayout>
      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="status-online" />
            <span className="text-[11px] text-muted-foreground font-medium tracking-wide uppercase">Live</span>
          </div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Security Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Real-time overview of your security posture</p>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => router.push("/simulation")}
            className="hidden sm:flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border hover:bg-muted text-muted-foreground hover:text-foreground text-sm transition-colors">
            <Zap className="w-3.5 h-3.5 text-yellow-400" /> Simulate
          </button>
          <button type="button" onClick={handleRefresh}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border hover:bg-muted text-muted-foreground hover:text-foreground text-sm transition-colors">
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      {/* ── Stat cards ── */}
      <motion.div variants={stagger.container} initial="hidden" animate="show"
        className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        {stats.map((s) => (
          <motion.div key={s.label} variants={stagger.item}>
            <div className="cyber-card p-5 relative overflow-hidden group cursor-default">
              <div className={`absolute left-0 top-0 bottom-0 w-[3px] rounded-r-full opacity-80 ${s.accentBar}`} />
              <div className={`absolute -top-8 -right-8 w-24 h-24 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-2xl ${s.glowClass}`} />
              <div className="flex items-center justify-between mb-4">
                <div className={`p-2 rounded-lg ${s.bg} border ${s.border}`}>
                  <s.icon className={`w-4 h-4 ${s.color}`} />
                </div>
                <div className={`flex items-center gap-1 text-xs font-semibold ${s.trendUp ? "text-green-400" : "text-red-400"}`}>
                  {s.trendUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                  {s.trend}
                </div>
              </div>
              <div className="text-[28px] font-bold text-foreground tracking-tight leading-none mb-1">{s.value}</div>
              <div className="text-xs text-muted-foreground font-medium">{s.label}</div>
            </div>
          </motion.div>
        ))}
      </motion.div>

      {/* ── Charts row ── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 mb-5">

        {/* Area chart */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.18 }}
          className="xl:col-span-2 cyber-card p-5 border border-border">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Incident Trend</h3>
              <p className="text-xs text-muted-foreground mt-0.5">Last 7 days</p>
            </div>
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 bg-primary rounded-full inline-block" />Total
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 bg-green-400 rounded-full inline-block" />Resolved
              </span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={210}>
            <AreaChart data={incidentTrendData} margin={{ top: 4, right: 4, bottom: 0, left: -22 }}>
              <defs>
                <linearGradient id="gradCyan" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="#00d4ff" stopOpacity={0.22} />
                  <stop offset="100%" stopColor="#00d4ff" stopOpacity={0.01} />
                </linearGradient>
                <linearGradient id="gradGreen" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="#10b981" stopOpacity={0.22} />
                  <stop offset="100%" stopColor="#10b981" stopOpacity={0.01} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="0" stroke="rgba(255,255,255,0.035)" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} cursor={{ stroke: "rgba(0,212,255,0.12)", strokeWidth: 1, strokeDasharray: "4 4" }} />
              <Area type="monotone" dataKey="incidents" stroke="#00d4ff" strokeWidth={2.5} fill="url(#gradCyan)"
                dot={false} activeDot={{ r: 5, fill: "#00d4ff", stroke: "#0a0e1a", strokeWidth: 2 }} name="Total Incidents" />
              <Area type="monotone" dataKey="resolved"  stroke="#10b981" strokeWidth={2.5} fill="url(#gradGreen)"
                dot={false} activeDot={{ r: 5, fill: "#10b981", stroke: "#0a0e1a", strokeWidth: 2 }} name="Resolved" />
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>

        {/* ── Custom active-shape donut ── */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.26 }}
          className="cyber-card p-5 border border-border flex flex-col">
          <div className="mb-3">
            <h3 className="text-sm font-semibold text-foreground">Attack Distribution</h3>
            <p className="text-xs text-muted-foreground mt-0.5">Hover a segment to inspect</p>
          </div>

          <div className="flex-1 flex flex-col items-center justify-center">
            <ResponsiveContainer width="100%" height={190}>
              <PieChart>
                <Pie
                  data={attackTypeData}
                  cx="50%"
                  cy="50%"
                  innerRadius={58}
                  outerRadius={82}
                  paddingAngle={3}
                  dataKey="value"
                  activeIndex={activeIndex}
                  activeShape={renderActiveShape}
                  onMouseEnter={onPieEnter}
                  onMouseLeave={onPieLeave}
                  strokeWidth={0}
                >
                  {attackTypeData.map((e, i) => (
                    <Cell key={i} fill={e.color} opacity={activeIndex === undefined || activeIndex === i ? 1 : 0.35} />
                  ))}
                  {/* Default center text when nothing is hovered */}
                  {activeIndex === undefined && (
                    <DonutCenter total={total} />
                  )}
                </Pie>
              </PieChart>
            </ResponsiveContainer>

            {/* Legend */}
            <div className="w-full space-y-2 mt-1">
              {attackTypeData.map((item, i) => (
                <div
                  key={item.name}
                  className="flex items-center gap-2 cursor-pointer group/item"
                  onMouseEnter={() => setActiveIndex(i)}
                  onMouseLeave={() => setActiveIndex(undefined)}
                >
                  <div className={`w-2.5 h-2.5 rounded-sm shrink-0 transition-transform group-hover/item:scale-125 ${item.dotClass}`} />
                  <span className="text-xs text-muted-foreground group-hover/item:text-foreground transition-colors flex-1">{item.name}</span>
                  <span className={`text-xs font-bold tabular-nums ${item.textClass}`}>{item.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>

      {/* ── Severity + Incidents row ── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 mb-5">

        {/* Severity column bars */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.32 }}
          className="cyber-card p-5 border border-border">
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-foreground">Severity Breakdown</h3>
            <p className="text-xs text-muted-foreground mt-0.5">Open incidents by level</p>
          </div>
          <ResponsiveContainer width="100%" height={192}>
            <BarChart data={severityData} margin={{ top: 4, right: 4, bottom: 0, left: -22 }}
              barCategoryGap="30%">
              <defs>
                <linearGradient id="d-sev-crit" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="#ef4444" stopOpacity={0.95} />
                  <stop offset="100%" stopColor="#ef4444" stopOpacity={0.45} />
                </linearGradient>
                <linearGradient id="d-sev-high" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="#f97316" stopOpacity={0.95} />
                  <stop offset="100%" stopColor="#f97316" stopOpacity={0.45} />
                </linearGradient>
                <linearGradient id="d-sev-med" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="#f59e0b" stopOpacity={0.95} />
                  <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.45} />
                </linearGradient>
                <linearGradient id="d-sev-low" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="#10b981" stopOpacity={0.95} />
                  <stop offset="100%" stopColor="#10b981" stopOpacity={0.45} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="0" stroke="rgba(255,255,255,0.04)" horizontal={true} vertical={false} />
              <XAxis dataKey="severity" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
              <Bar dataKey="count" radius={[5, 5, 0, 0]} name="Count" maxBarSize={38}>
                {severityData.map((d) => (
                  <Cell key={d.severity} fill={`url(#${d.gradId})`} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Recent incidents */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.38 }}
          className="xl:col-span-2 cyber-card border border-border overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-border">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Recent Incidents</h3>
              <p className="text-xs text-muted-foreground mt-0.5">Latest activity</p>
            </div>
            <button type="button" onClick={() => router.push("/incidents")}
              className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors font-medium">
              View all <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="divide-y divide-border/60">
            {recentIncidents.map((inc, i) => (
              <motion.div key={inc.id}
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.38 + i * 0.05 }}
                className="flex items-center gap-3 px-5 py-3 hover:bg-muted/20 transition-colors cursor-pointer group"
                onClick={() => router.push(`/incidents?id=${inc.id}`)}>
                <SeverityBadge severity={inc.severity as "critical" | "high" | "medium" | "low"} size="sm" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground truncate group-hover:text-primary transition-colors">{inc.description}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[11px] text-purple-400 font-medium">{inc.threat_class}</span>
                    <span className="text-muted-foreground/50">·</span>
                    <span className="text-[11px] text-muted-foreground">{formatRelativeTime(inc.created_at)}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <StatusPill status={inc.status} />
                  <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/40 group-hover:text-primary transition-colors" />
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* ── Quick analysis ── */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.48 }}
        className="cyber-card border border-border p-5">
        <div className="flex items-center gap-3 mb-3">
          <div className="p-1.5 rounded-lg bg-primary/10 border border-primary/20">
            <Zap className="w-4 h-4 text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">Quick Incident Analysis</h3>
            <p className="text-xs text-muted-foreground">Describe a threat and the AI pipeline will triage it instantly</p>
          </div>
        </div>
        <div className="flex gap-2.5">
          <input type="text" value={quickAnalysis} onChange={e => setQuickAnalysis(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleQuickAnalysis()}
            placeholder="e.g. Ransomware detected on finance servers, encrypted 200 files..."
            className="flex-1 cyber-input" />
          <button type="button" onClick={handleQuickAnalysis} disabled={!quickAnalysis.trim()} className="btn-primary shrink-0">
            Analyze <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </motion.div>
    </DashboardLayout>
  );
}
