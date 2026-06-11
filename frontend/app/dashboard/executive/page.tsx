"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Shield, AlertTriangle, Clock, TrendingUp, TrendingDown, Activity,
  Target, RefreshCw, Server, BarChart2, Percent, Zap,
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, Sector,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LabelList,
} from "recharts";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import api from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────
type DateRange = "7d" | "30d" | "90d";
type SeverityFilter = "all" | "critical" | "high" | "medium" | "low";

interface MetricCard {
  label: string;
  value: string | number;
  unit?: string;
  trend?: string;
  trendUp?: boolean;
  icon: React.ElementType;
  color: string;
  bgColor: string;
  borderColor: string;
}

interface RiskyAsset {
  ip: string;
  hostname: string;
  incident_count: number;
  risk_score: number;
  last_seen: string;
  severity: "critical" | "high" | "medium" | "low";
}

// ─── Mock Data ────────────────────────────────────────────────────────────────
function generateTimeSeriesData(days: number) {
  const data = [];
  const now = new Date();
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    const label =
      days <= 7
        ? date.toLocaleDateString("en-US", { weekday: "short" })
        : days <= 30
        ? date.toLocaleDateString("en-US", { month: "short", day: "numeric" })
        : `W${Math.ceil((days - i) / 7)}`;
    const incidents = Math.floor(Math.random() * 15) + 3;
    const resolved = Math.floor(incidents * (0.7 + Math.random() * 0.25));
    data.push({ date: label, incidents, resolved });
  }
  return data;
}

const MOCK_METRICS = {
  total_incidents: 143, critical_incidents: 8, high_incidents: 23,
  medium_incidents: 45, low_incidents: 67, avg_response_time_minutes: 18.4,
  escalation_rate: 12, false_positive_rate: 8, mttr_hours: 4.2,
  active_threats: 14, sla_breach_rate: 6.3,
};

const ATTACK_TYPE_DATA = [
  { name: "Ransomware",    value: 28, color: "#ef4444", dot: "bg-red-500",    text: "text-red-400"    },
  { name: "Phishing",      value: 22, color: "#f97316", dot: "bg-orange-500", text: "text-orange-400" },
  { name: "DDoS",          value: 18, color: "#f59e0b", dot: "bg-amber-500",  text: "text-amber-400"  },
  { name: "SQL Injection", value: 15, color: "#7c3aed", dot: "bg-violet-600", text: "text-violet-400" },
  { name: "Zero-Day",      value: 10, color: "#00d4ff", dot: "bg-cyan-400",   text: "text-primary"    },
  { name: "Other",         value:  7, color: "#64748b", dot: "bg-slate-500",  text: "text-slate-400"  },
];

const SEVERITY_DATA = [
  { severity: "Critical", count:  8, fill: "#ef4444", gradId: "x-sev-crit" },
  { severity: "High",     count: 23, fill: "#f97316", gradId: "x-sev-high" },
  { severity: "Medium",   count: 45, fill: "#f59e0b", gradId: "x-sev-med"  },
  { severity: "Low",      count: 67, fill: "#10b981", gradId: "x-sev-low"  },
];

// Tactic-to-color mapping (static, so Tailwind can be satisfied)
const TACTIC_COLORS: Record<string, string> = {
  "Impact":           "#ef4444",
  "Initial Access":   "#f97316",
  "Execution":        "#f59e0b",
  "Defense Evasion":  "#7c3aed",
  "Privilege Esc.":   "#ec4899",
  "Lateral Movement": "#00d4ff",
  "Exfiltration":     "#10b981",
  "C2":               "#6366f1",
  "Credential Access":"#a855f7",
};

const MITRE_DATA = [
  { technique: "T1486 Data Encrypted", count: 28, tactic: "Impact",           fill: TACTIC_COLORS["Impact"],           gradId: "mt-x0" },
  { technique: "T1566 Phishing",        count: 24, tactic: "Initial Access",   fill: TACTIC_COLORS["Initial Access"],   gradId: "mt-x1" },
  { technique: "T1190 Public Exploit",  count: 19, tactic: "Initial Access",   fill: TACTIC_COLORS["Initial Access"],   gradId: "mt-x2" },
  { technique: "T1059 Command Shell",   count: 17, tactic: "Execution",        fill: TACTIC_COLORS["Execution"],        gradId: "mt-x3" },
  { technique: "T1078 Valid Accounts",  count: 15, tactic: "Defense Evasion",  fill: TACTIC_COLORS["Defense Evasion"],  gradId: "mt-x4" },
  { technique: "T1055 Process Inject",  count: 13, tactic: "Privilege Esc.",   fill: TACTIC_COLORS["Privilege Esc."],   gradId: "mt-x5" },
  { technique: "T1021 Remote Services", count: 11, tactic: "Lateral Movement", fill: TACTIC_COLORS["Lateral Movement"], gradId: "mt-x6" },
  { technique: "T1048 Data Exfil",      count:  9, tactic: "Exfiltration",     fill: TACTIC_COLORS["Exfiltration"],     gradId: "mt-x7" },
  { technique: "T1071 App Layer",       count:  8, tactic: "C2",               fill: TACTIC_COLORS["C2"],               gradId: "mt-x8" },
  { technique: "T1110 Brute Force",     count:  7, tactic: "Credential Access",fill: TACTIC_COLORS["Credential Access"],gradId: "mt-x9" },
];

const RISKY_ASSETS: RiskyAsset[] = [
  { ip: "192.168.10.45", hostname: "finance-ws-01",  incident_count: 12, risk_score: 94, last_seen: "2 min ago",  severity: "critical" },
  { ip: "10.0.0.8",      hostname: "db-prod-01",     incident_count:  8, risk_score: 87, last_seen: "15 min ago", severity: "critical" },
  { ip: "192.168.1.102", hostname: "web-srv-03",     incident_count:  7, risk_score: 75, last_seen: "1 hr ago",   severity: "high"     },
  { ip: "10.0.1.55",     hostname: "hr-ws-12",       incident_count:  5, risk_score: 68, last_seen: "3 hr ago",   severity: "high"     },
  { ip: "172.16.0.22",   hostname: "mail-relay-01",  incident_count:  4, risk_score: 52, last_seen: "6 hr ago",   severity: "medium"   },
];

const SEVERITY_TEXT: Record<string, string> = {
  critical: "text-red-400", high: "text-orange-400", medium: "text-amber-400", low: "text-green-400",
};
const RISK_BAR: (s: number) => string = (s) =>
  s >= 80 ? "bg-red-500" : s >= 60 ? "bg-orange-500" : s >= 40 ? "bg-amber-500" : "bg-green-500";
const RISK_TEXT: (s: number) => string = (s) =>
  s >= 80 ? "text-red-400" : s >= 60 ? "text-orange-400" : s >= 40 ? "text-amber-400" : "text-green-400";

// ─── Tooltip ──────────────────────────────────────────────────────────────────
const SERIES_DOTS: Record<string, string> = {
  Incidents: "bg-primary", Resolved: "bg-green-400",
  Count: "bg-slate-400", Occurrences: "bg-violet-500",
};

function ChartTooltip({
  active, payload, label,
}: {
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
          <div className={`w-2 h-2 rounded-full shrink-0 ${SERIES_DOTS[e.name] ?? "bg-muted-foreground"}`} />
          <span className="text-foreground">{e.name}: <strong>{e.value}</strong></span>
        </div>
      ))}
    </div>
  );
}

// ─── Active-shape donut ───────────────────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const renderActiveShape = (props: any) => {
  const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill, payload, value, percent } = props;
  return (
    <g>
      <text x={cx} y={cy - 9} textAnchor="middle" fill="#e2e8f0" fontSize={22} fontWeight={700}>{value}</text>
      <text x={cx} y={cy + 10} textAnchor="middle" fill="#94a3b8" fontSize={10}>{payload.name}</text>
      <text x={cx} y={cy + 25} textAnchor="middle" fill={fill} fontSize={11} fontWeight={600}>
        {(percent * 100).toFixed(0)}%
      </text>
      <Sector cx={cx} cy={cy} innerRadius={innerRadius} outerRadius={outerRadius + 8}
        startAngle={startAngle} endAngle={endAngle} fill={fill} opacity={0.95} />
      <Sector cx={cx} cy={cy} innerRadius={outerRadius + 10} outerRadius={outerRadius + 14}
        startAngle={startAngle} endAngle={endAngle} fill={fill} opacity={0.28} />
    </g>
  );
};

// Default center label when nothing hovered
function DonutDefaultCenter({ cx = 0, cy = 0, total }: { cx?: number; cy?: number; total: number }) {
  return (
    <g>
      <text x={cx} y={cy - 6} textAnchor="middle" fill="#e2e8f0" fontSize={22} fontWeight={700}>{total}</text>
      <text x={cx} y={cy + 12} textAnchor="middle" fill="#64748b" fontSize={10}>incidents</text>
    </g>
  );
}

// ─── Animated number counter ──────────────────────────────────────────────────
function AnimatedNumber({ value, suffix = "" }: { value: number; suffix?: string }) {
  const [displayed, setDisplayed] = useState(0);
  useEffect(() => {
    const duration = 1200;
    const start = Date.now();
    const animate = () => {
      const elapsed = Date.now() - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayed(Math.round(eased * value));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [value]);
  return <span>{displayed}{suffix}</span>;
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function ExecutiveDashboardPage() {
  const [dateRange, setDateRange]       = useState<DateRange>("30d");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [metrics, setMetrics]           = useState(MOCK_METRICS);
  const [timeSeriesData, setTimeSeriesData] = useState(() => generateTimeSeriesData(30));
  const [activeIndex, setActiveIndex]   = useState<number | undefined>(undefined);

  const onPieEnter  = useCallback((_: unknown, i: number) => setActiveIndex(i), []);
  const onPieLeave  = useCallback(() => setActiveIndex(undefined), []);

  const fetchMetrics = async () => {
    try {
      const res = await api.get("/dashboard/executive-metrics", { params: { range: dateRange } });
      setMetrics({ ...MOCK_METRICS, ...res.data });
    } catch { /* use mock */ }
  };

  useEffect(() => {
    fetchMetrics();
    const days = dateRange === "7d" ? 7 : dateRange === "30d" ? 30 : 90;
    setTimeSeriesData(generateTimeSeriesData(days));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchMetrics();
    const days = dateRange === "7d" ? 7 : dateRange === "30d" ? 30 : 90;
    setTimeSeriesData(generateTimeSeriesData(days));
    setTimeout(() => setIsRefreshing(false), 800);
    toast.success("Dashboard refreshed");
  };

  const filteredSeverityData =
    severityFilter === "all"
      ? SEVERITY_DATA
      : SEVERITY_DATA.filter((d) => d.severity.toLowerCase() === severityFilter);

  const total = ATTACK_TYPE_DATA.reduce((s, d) => s + d.value, 0);

  const topMetrics: MetricCard[] = [
    { label: "Total Incidents",   value: metrics.total_incidents,           trend: "+12%",       trendUp: true,  icon: Shield,        color: "text-primary",    bgColor: "bg-primary/10",    borderColor: "border-primary/20"    },
    { label: "Critical Incidents",value: metrics.critical_incidents,        trend: "-2 this week",trendUp: false, icon: AlertTriangle, color: "text-red-400",    bgColor: "bg-red-500/10",    borderColor: "border-red-500/20"    },
    { label: "Avg Response Time", value: metrics.avg_response_time_minutes, unit: "min", trend: "-3.2 min", trendUp: false, icon: Clock, color: "text-green-400", bgColor: "bg-green-500/10", borderColor: "border-green-500/20"  },
    { label: "Escalation Rate",   value: metrics.escalation_rate,           unit: "%",   trend: "-1.5%",    trendUp: false, icon: TrendingUp, color: "text-orange-400", bgColor: "bg-orange-500/10", borderColor: "border-orange-500/20" },
  ];

  const bottomMetrics: MetricCard[] = [
    { label: "False Positive Rate",value: metrics.false_positive_rate, unit: "%",   trend: "-0.8%",  trendUp: false, icon: Percent,   color: "text-purple-400", bgColor: "bg-purple-500/10", borderColor: "border-purple-500/20" },
    { label: "MTTR",               value: metrics.mttr_hours,          unit: "hrs", trend: "-0.3 hrs",trendUp: false, icon: BarChart2, color: "text-cyan-400",   bgColor: "bg-cyan-500/10",   borderColor: "border-cyan-500/20"   },
    { label: "Active Threats",     value: metrics.active_threats,                   trend: "+2",      trendUp: true,  icon: Zap,       color: "text-red-400",    bgColor: "bg-red-500/10",    borderColor: "border-red-500/20"    },
    { label: "SLA Breach Rate",    value: metrics.sla_breach_rate,     unit: "%",   trend: "+0.4%",   trendUp: true,  icon: Activity,  color: "text-amber-400",  bgColor: "bg-amber-500/10",  borderColor: "border-amber-500/20"  },
  ];

  return (
    <DashboardLayout>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>

        {/* ── Header ── */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Executive SOC Dashboard</h1>
            <p className="text-muted-foreground text-sm mt-1">Comprehensive security operations analytics &amp; KPIs</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex gap-1 border border-border rounded-lg p-1">
              {(["7d", "30d", "90d"] as DateRange[]).map((r) => (
                <button key={r} type="button" onClick={() => setDateRange(r)}
                  className={cn("px-3 py-1.5 rounded text-xs font-medium transition-all",
                    dateRange === r ? "bg-primary text-background shadow-[0_0_10px_rgba(0,212,255,0.2)]" : "text-muted-foreground hover:text-foreground")}>
                  {r}
                </button>
              ))}
            </div>
            <button type="button" onClick={handleRefresh}
              className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border hover:bg-muted text-muted-foreground hover:text-foreground text-sm transition-colors">
              <RefreshCw className={cn("w-4 h-4", isRefreshing && "animate-spin")} /> Refresh
            </button>
          </div>
        </div>

        {/* ── Severity Filter ── */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {(["all", "critical", "high", "medium", "low"] as SeverityFilter[]).map((sev) => (
            <button key={sev} type="button" onClick={() => setSeverityFilter(sev)}
              className={cn("px-3 py-1.5 rounded-lg text-xs font-medium border transition-all capitalize",
                severityFilter === sev
                  ? { all: "bg-primary/20 border-primary/50 text-primary", critical: "bg-red-500/20 border-red-500/50 text-red-400", high: "bg-orange-500/20 border-orange-500/50 text-orange-400", medium: "bg-amber-500/20 border-amber-500/50 text-amber-400", low: "bg-green-500/20 border-green-500/50 text-green-400" }[sev]
                  : "border-border text-muted-foreground hover:text-foreground")}>
              {sev === "all" ? "All Severities" : sev}
            </button>
          ))}
        </div>

        {/* ── Top Metrics ── */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-5">
          {topMetrics.map((m, i) => (
            <motion.div key={m.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: i * 0.07 }}
              className={cn("cyber-card p-5 border", m.borderColor)}>
              <div className="flex items-center justify-between mb-3">
                <div className={cn("p-2 rounded-lg border", m.bgColor, m.borderColor)}>
                  <m.icon className={cn("w-5 h-5", m.color)} />
                </div>
                <div className={cn("flex items-center gap-1 text-xs font-medium", m.trendUp ? "text-red-400" : "text-green-400")}>
                  {m.trendUp ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />} {m.trend}
                </div>
              </div>
              <div className={cn("text-2xl font-black mb-1", m.color)}>
                <AnimatedNumber value={typeof m.value === "number" ? m.value : parseFloat(String(m.value))} suffix={m.unit ?? ""} />
              </div>
              <div className="text-xs text-muted-foreground">{m.label}</div>
            </motion.div>
          ))}
        </div>

        {/* ── Bottom Metrics ── */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
          {bottomMetrics.map((m, i) => (
            <motion.div key={m.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.28 + i * 0.07 }}
              className={cn("cyber-card p-5 border", m.borderColor)}>
              <div className="flex items-center justify-between mb-3">
                <div className={cn("p-2 rounded-lg border", m.bgColor, m.borderColor)}>
                  <m.icon className={cn("w-5 h-5", m.color)} />
                </div>
                <div className={cn("flex items-center gap-1 text-xs font-medium", m.trendUp ? "text-red-400" : "text-green-400")}>
                  {m.trendUp ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />} {m.trend}
                </div>
              </div>
              <div className={cn("text-2xl font-black mb-1", m.color)}>
                <AnimatedNumber value={typeof m.value === "number" ? m.value : parseFloat(String(m.value))} suffix={m.unit ?? ""} />
              </div>
              <div className="text-xs text-muted-foreground">{m.label}</div>
            </motion.div>
          ))}
        </div>

        {/* ── Charts Row 1 — Area + Donut ── */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 mb-5">

          {/* Incidents Over Time */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="xl:col-span-2 cyber-card p-5 border border-border">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Activity className="w-4 h-4 text-primary" /> Incidents Over Time
                <span className="text-xs text-muted-foreground font-normal">— {dateRange}</span>
              </h3>
              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 bg-primary rounded-full inline-block" />Incidents
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 bg-green-400 rounded-full inline-block" />Resolved
                </span>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={230}>
              <AreaChart data={timeSeriesData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <defs>
                  <linearGradient id="execGradCyan" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor="#00d4ff" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#00d4ff" stopOpacity={0.01} />
                  </linearGradient>
                  <linearGradient id="execGradGreen" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor="#10b981" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#10b981" stopOpacity={0.01} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="0" stroke="rgba(255,255,255,0.035)" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTooltip />} cursor={{ stroke: "rgba(0,212,255,0.12)", strokeWidth: 1, strokeDasharray: "4 4" }} />
                <Area type="monotone" dataKey="incidents" stroke="#00d4ff" strokeWidth={2.5} fill="url(#execGradCyan)"
                  dot={false} activeDot={{ r: 5, fill: "#00d4ff", stroke: "#0a0e1a", strokeWidth: 2 }} name="Incidents" />
                <Area type="monotone" dataKey="resolved"  stroke="#10b981" strokeWidth={2.5} fill="url(#execGradGreen)"
                  dot={false} activeDot={{ r: 5, fill: "#10b981", stroke: "#0a0e1a", strokeWidth: 2 }} name="Resolved" />
              </AreaChart>
            </ResponsiveContainer>
          </motion.div>

          {/* Attack Types — custom active-shape donut */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.35 }}
            className="cyber-card p-5 border border-border flex flex-col">
            <h3 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
              <Target className="w-4 h-4 text-primary" /> Attack Types
            </h3>
            <p className="text-[11px] text-muted-foreground mb-2">Hover a segment to inspect</p>

            <div className="flex-1 flex flex-col items-center">
              <ResponsiveContainer width="100%" height={195}>
                <PieChart>
                  <Pie
                    data={ATTACK_TYPE_DATA}
                    cx="50%" cy="50%"
                    innerRadius={60} outerRadius={84}
                    paddingAngle={3}
                    dataKey="value"
                    activeIndex={activeIndex}
                    activeShape={renderActiveShape}
                    onMouseEnter={onPieEnter}
                    onMouseLeave={onPieLeave}
                    strokeWidth={0}
                  >
                    {ATTACK_TYPE_DATA.map((e, i) => (
                      <Cell key={i} fill={e.color} opacity={activeIndex === undefined || activeIndex === i ? 1 : 0.3} />
                    ))}
                    {activeIndex === undefined && <DonutDefaultCenter total={total} />}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>

              {/* Legend */}
              <div className="w-full grid grid-cols-1 gap-1.5">
                {ATTACK_TYPE_DATA.map((item, i) => (
                  <div key={item.name}
                    className="flex items-center gap-2 cursor-pointer group/item"
                    onMouseEnter={() => setActiveIndex(i)}
                    onMouseLeave={() => setActiveIndex(undefined)}>
                    <div className={`w-2.5 h-2.5 rounded-sm shrink-0 transition-transform group-hover/item:scale-125 ${item.dot}`} />
                    <span className="text-[11px] text-muted-foreground group-hover/item:text-foreground transition-colors flex-1">{item.name}</span>
                    <span className={`text-[11px] font-bold tabular-nums ${item.text}`}>{item.value}%</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>

        {/* ── Charts Row 2 — Severity + MITRE ── */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 mb-5">

          {/* Severity Heatmap — vertical bars */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="cyber-card p-5 border border-border">
            <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" /> Severity Distribution
            </h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={filteredSeverityData} margin={{ top: 4, right: 4, bottom: 0, left: -22 }} barCategoryGap="30%">
                <defs>
                  <linearGradient id="x-sev-crit" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor="#ef4444" stopOpacity={0.95} />
                    <stop offset="100%" stopColor="#ef4444" stopOpacity={0.4}  />
                  </linearGradient>
                  <linearGradient id="x-sev-high" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor="#f97316" stopOpacity={0.95} />
                    <stop offset="100%" stopColor="#f97316" stopOpacity={0.4}  />
                  </linearGradient>
                  <linearGradient id="x-sev-med" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor="#f59e0b" stopOpacity={0.95} />
                    <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.4}  />
                  </linearGradient>
                  <linearGradient id="x-sev-low" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor="#10b981" stopOpacity={0.95} />
                    <stop offset="100%" stopColor="#10b981" stopOpacity={0.4}  />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="0" stroke="rgba(255,255,255,0.04)" horizontal={true} vertical={false} />
                <XAxis dataKey="severity" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                <Bar dataKey="count" radius={[5, 5, 0, 0]} name="Count" maxBarSize={40}>
                  {filteredSeverityData.map((d) => (
                    <Cell key={d.severity} fill={`url(#${d.gradId})`} />
                  ))}
                  <LabelList dataKey="count" position="top" style={{ fill: "#94a3b8", fontSize: 10 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </motion.div>

          {/* MITRE ATT&CK */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.45 }}
            className="xl:col-span-2 cyber-card p-5 border border-border">
            <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
              <Shield className="w-4 h-4 text-violet-400" /> Top 10 MITRE ATT&amp;CK Techniques
            </h3>
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={MITRE_DATA} layout="vertical" margin={{ top: 2, right: 40, bottom: 0, left: 4 }}>
                <defs>
                  <linearGradient id="mt-x0" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#ef4444" stopOpacity={0.9} /><stop offset="100%" stopColor="#ef4444" stopOpacity={0.55} /></linearGradient>
                  <linearGradient id="mt-x1" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#f97316" stopOpacity={0.9} /><stop offset="100%" stopColor="#f97316" stopOpacity={0.55} /></linearGradient>
                  <linearGradient id="mt-x2" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#f97316" stopOpacity={0.9} /><stop offset="100%" stopColor="#f97316" stopOpacity={0.55} /></linearGradient>
                  <linearGradient id="mt-x3" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#f59e0b" stopOpacity={0.9} /><stop offset="100%" stopColor="#f59e0b" stopOpacity={0.55} /></linearGradient>
                  <linearGradient id="mt-x4" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#7c3aed" stopOpacity={0.9} /><stop offset="100%" stopColor="#7c3aed" stopOpacity={0.55} /></linearGradient>
                  <linearGradient id="mt-x5" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#ec4899" stopOpacity={0.9} /><stop offset="100%" stopColor="#ec4899" stopOpacity={0.55} /></linearGradient>
                  <linearGradient id="mt-x6" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#00d4ff" stopOpacity={0.9} /><stop offset="100%" stopColor="#00d4ff" stopOpacity={0.55} /></linearGradient>
                  <linearGradient id="mt-x7" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#10b981" stopOpacity={0.9} /><stop offset="100%" stopColor="#10b981" stopOpacity={0.55} /></linearGradient>
                  <linearGradient id="mt-x8" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#6366f1" stopOpacity={0.9} /><stop offset="100%" stopColor="#6366f1" stopOpacity={0.55} /></linearGradient>
                  <linearGradient id="mt-x9" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#a855f7" stopOpacity={0.9} /><stop offset="100%" stopColor="#a855f7" stopOpacity={0.55} /></linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="0" stroke="rgba(255,255,255,0.04)" horizontal={false} vertical={true} />
                <XAxis type="number" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis dataKey="technique" type="category" tick={{ fill: "#94a3b8", fontSize: 9 }}
                  axisLine={false} tickLine={false} width={118} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                <Bar dataKey="count" radius={[0, 5, 5, 0]} name="Occurrences" maxBarSize={14}>
                  {MITRE_DATA.map((d) => (
                    <Cell key={d.gradId} fill={`url(#${d.gradId})`} />
                  ))}
                  <LabelList dataKey="count" position="right" style={{ fill: "#94a3b8", fontSize: 9 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </motion.div>
        </div>

        {/* ── Risky Assets ── */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="cyber-card border border-border overflow-hidden">
          <div className="px-5 py-4 border-b border-border flex items-center gap-2">
            <Server className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-semibold text-foreground">Risky Assets</h3>
            <span className="text-xs text-muted-foreground ml-1">— highest incident frequency</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {["IP Address", "Hostname", "Incidents", "Risk Score", "Last Seen", "Severity"].map((h) => (
                    <th key={h} className="px-5 py-3 text-xs font-medium text-muted-foreground text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {RISKY_ASSETS.map((asset, i) => (
                  <motion.tr key={asset.ip}
                    initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.55 + i * 0.05 }}
                    className="hover:bg-muted/30 transition-colors">
                    <td className="px-5 py-3 font-mono text-xs text-primary">{asset.ip}</td>
                    <td className="px-5 py-3 text-foreground">{asset.hostname}</td>
                    <td className="px-5 py-3"><span className="font-mono font-bold">{asset.incident_count}</span></td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                          <div className={cn("h-full rounded-full", RISK_BAR(asset.risk_score))}
                            style={{ width: `${asset.risk_score}%` }} />
                        </div>
                        <span className={cn("text-xs font-mono font-bold", RISK_TEXT(asset.risk_score))}>{asset.risk_score}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3 text-xs text-muted-foreground">{asset.last_seen}</td>
                    <td className="px-5 py-3">
                      <span className={cn("text-xs font-semibold capitalize", SEVERITY_TEXT[asset.severity])}>{asset.severity}</span>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>

      </motion.div>
    </DashboardLayout>
  );
}
