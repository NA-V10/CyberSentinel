"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Shield,
  AlertTriangle,
  Clock,
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  RefreshCw,
  Server,
  BarChart2,
  Percent,
  Zap,
} from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import api from "@/lib/api";

// ─── Types ──────────────────────────────────────────────────────────────────

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

// ─── Mock Data ───────────────────────────────────────────────────────────────

function generateTimeSeriesData(days: number) {
  const data = [];
  const now = new Date();
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    const label = days <= 7
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
  total_incidents: 143,
  critical_incidents: 8,
  high_incidents: 23,
  medium_incidents: 45,
  low_incidents: 67,
  avg_response_time_minutes: 18.4,
  escalation_rate: 12,
  false_positive_rate: 8,
  mttr_hours: 4.2,
  active_threats: 14,
  sla_breach_rate: 6.3,
};

const ATTACK_TYPE_DATA = [
  { name: "Ransomware", value: 28, color: "#ef4444" },
  { name: "Phishing", value: 22, color: "#f97316" },
  { name: "DDoS", value: 18, color: "#f59e0b" },
  { name: "SQL Injection", value: 15, color: "#7c3aed" },
  { name: "Zero-Day", value: 10, color: "#00d4ff" },
  { name: "Other", value: 7, color: "#64748b" },
];

const SEVERITY_DATA = [
  { severity: "Critical", count: 8, fill: "#ef4444" },
  { severity: "High", count: 23, fill: "#f97316" },
  { severity: "Medium", count: 45, fill: "#f59e0b" },
  { severity: "Low", count: 67, fill: "#10b981" },
];

const MITRE_DATA = [
  { technique: "T1486 Data Encrypted", count: 28, tactic: "Impact" },
  { technique: "T1566 Phishing", count: 24, tactic: "Initial Access" },
  { technique: "T1190 Public Exploit", count: 19, tactic: "Initial Access" },
  { technique: "T1059 Command Shell", count: 17, tactic: "Execution" },
  { technique: "T1078 Valid Accounts", count: 15, tactic: "Defense Evasion" },
  { technique: "T1055 Process Inject", count: 13, tactic: "Privilege Esc." },
  { technique: "T1021 Remote Services", count: 11, tactic: "Lateral Movement" },
  { technique: "T1048 Data Exfil", count: 9, tactic: "Exfiltration" },
  { technique: "T1071 App Layer", count: 8, tactic: "C2" },
  { technique: "T1110 Brute Force", count: 7, tactic: "Credential Access" },
];

const RISKY_ASSETS: RiskyAsset[] = [
  { ip: "192.168.10.45", hostname: "finance-ws-01", incident_count: 12, risk_score: 94, last_seen: "2 min ago", severity: "critical" },
  { ip: "10.0.0.8", hostname: "db-prod-01", incident_count: 8, risk_score: 87, last_seen: "15 min ago", severity: "critical" },
  { ip: "192.168.1.102", hostname: "web-srv-03", incident_count: 7, risk_score: 75, last_seen: "1 hr ago", severity: "high" },
  { ip: "10.0.1.55", hostname: "hr-ws-12", incident_count: 5, risk_score: 68, last_seen: "3 hr ago", severity: "high" },
  { ip: "172.16.0.22", hostname: "mail-relay-01", incident_count: 4, risk_score: 52, last_seen: "6 hr ago", severity: "medium" },
];

const SEVERITY_COLORS: Record<string, string> = {
  critical: "text-red-400",
  high: "text-orange-400",
  medium: "text-amber-400",
  low: "text-green-400",
};

// ─── Sub-components ──────────────────────────────────────────────────────────

const CustomTooltip = ({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-card border border-border rounded-lg p-3 text-xs shadow-xl">
        <p className="text-muted-foreground mb-1.5">{label}</p>
        {payload.map((entry, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full" style={{ background: entry.color }} />
            <span className="text-foreground">{entry.name}: <span className="font-mono font-semibold">{entry.value}</span></span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

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

  return (
    <span>
      {displayed}
      {suffix}
    </span>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ExecutiveDashboardPage() {
  const [dateRange, setDateRange] = useState<DateRange>("30d");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [metrics, setMetrics] = useState(MOCK_METRICS);
  const [timeSeriesData, setTimeSeriesData] = useState(() => generateTimeSeriesData(30));

  // ── Fetch metrics ──
  const fetchMetrics = async () => {
    try {
      const res = await api.get("/dashboard/executive-metrics", { params: { range: dateRange } });
      setMetrics({ ...MOCK_METRICS, ...res.data });
    } catch {
      // Use mock data silently
    }
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

  // ── Filtered severity data ──
  const filteredSeverityData =
    severityFilter === "all"
      ? SEVERITY_DATA
      : SEVERITY_DATA.filter((d) => d.severity.toLowerCase() === severityFilter);

  // ── Metric cards ──
  const topMetrics: MetricCard[] = [
    {
      label: "Total Incidents",
      value: metrics.total_incidents,
      trend: "+12%",
      trendUp: true,
      icon: Shield,
      color: "text-primary",
      bgColor: "bg-primary/10",
      borderColor: "border-primary/20",
    },
    {
      label: "Critical Incidents",
      value: metrics.critical_incidents,
      trend: "-2 this week",
      trendUp: false,
      icon: AlertTriangle,
      color: "text-red-400",
      bgColor: "bg-red-500/10",
      borderColor: "border-red-500/20",
    },
    {
      label: "Avg Response Time",
      value: metrics.avg_response_time_minutes,
      unit: "min",
      trend: "-3.2 min",
      trendUp: false,
      icon: Clock,
      color: "text-green-400",
      bgColor: "bg-green-500/10",
      borderColor: "border-green-500/20",
    },
    {
      label: "Escalation Rate",
      value: metrics.escalation_rate,
      unit: "%",
      trend: "-1.5%",
      trendUp: false,
      icon: TrendingUp,
      color: "text-orange-400",
      bgColor: "bg-orange-500/10",
      borderColor: "border-orange-500/20",
    },
  ];

  const bottomMetrics: MetricCard[] = [
    {
      label: "False Positive Rate",
      value: metrics.false_positive_rate,
      unit: "%",
      trend: "-0.8%",
      trendUp: false,
      icon: Percent,
      color: "text-purple-400",
      bgColor: "bg-purple-500/10",
      borderColor: "border-purple-500/20",
    },
    {
      label: "MTTR",
      value: metrics.mttr_hours,
      unit: "hrs",
      trend: "-0.3 hrs",
      trendUp: false,
      icon: BarChart2,
      color: "text-cyan-400",
      bgColor: "bg-cyan-500/10",
      borderColor: "border-cyan-500/20",
    },
    {
      label: "Active Threats",
      value: metrics.active_threats,
      trend: "+2",
      trendUp: true,
      icon: Zap,
      color: "text-red-400",
      bgColor: "bg-red-500/10",
      borderColor: "border-red-500/20",
    },
    {
      label: "SLA Breach Rate",
      value: metrics.sla_breach_rate,
      unit: "%",
      trend: "+0.4%",
      trendUp: true,
      icon: Activity,
      color: "text-amber-400",
      bgColor: "bg-amber-500/10",
      borderColor: "border-amber-500/20",
    },
  ];

  return (
    <DashboardLayout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        {/* ── Header ── */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Executive SOC Dashboard</h1>
            <p className="text-muted-foreground text-sm mt-1">
              Comprehensive security operations analytics &amp; KPIs
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Date range */}
            <div className="flex gap-1 border border-border rounded-lg p-1">
              {(["7d", "30d", "90d"] as DateRange[]).map((r) => (
                <button
                  key={r}
                  onClick={() => setDateRange(r)}
                  className={cn(
                    "px-3 py-1.5 rounded text-xs font-medium transition-all",
                    dateRange === r
                      ? "bg-primary text-background shadow-[0_0_10px_rgba(0,212,255,0.2)]"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {r}
                </button>
              ))}
            </div>
            <button
              onClick={handleRefresh}
              className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border hover:bg-muted text-muted-foreground hover:text-foreground text-sm transition-colors"
            >
              <RefreshCw className={cn("w-4 h-4", isRefreshing && "animate-spin")} />
              Refresh
            </button>
          </div>
        </div>

        {/* ── Severity Filter Chips ── */}
        <div className="flex gap-2 mb-6">
          {(["all", "critical", "high", "medium", "low"] as SeverityFilter[]).map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-medium border transition-all capitalize",
                severityFilter === sev
                  ? {
                      all: "bg-primary/20 border-primary/50 text-primary",
                      critical: "bg-red-500/20 border-red-500/50 text-red-400",
                      high: "bg-orange-500/20 border-orange-500/50 text-orange-400",
                      medium: "bg-amber-500/20 border-amber-500/50 text-amber-400",
                      low: "bg-green-500/20 border-green-500/50 text-green-400",
                    }[sev]
                  : "border-border text-muted-foreground hover:text-foreground hover:border-border/80"
              )}
            >
              {sev === "all" ? "All Severities" : sev}
            </button>
          ))}
        </div>

        {/* ── Top Metrics Row ── */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-5">
          {topMetrics.map((metric, i) => {
            const Icon = metric.icon;
            return (
              <motion.div
                key={metric.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: i * 0.07 }}
                className={cn("cyber-card p-5 border", metric.borderColor)}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className={cn("p-2 rounded-lg border", metric.bgColor, metric.borderColor)}>
                    <Icon className={cn("w-5 h-5", metric.color)} />
                  </div>
                  <div className={cn("flex items-center gap-1 text-xs font-medium", metric.trendUp ? "text-red-400" : "text-green-400")}>
                    {metric.trendUp ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                    {metric.trend}
                  </div>
                </div>
                <div className={cn("text-2xl font-black mb-1", metric.color)}>
                  <AnimatedNumber value={typeof metric.value === "number" ? metric.value : parseFloat(String(metric.value))} suffix={metric.unit || ""} />
                </div>
                <div className="text-xs text-muted-foreground">{metric.label}</div>
              </motion.div>
            );
          })}
        </div>

        {/* ── Bottom Metrics Row ── */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
          {bottomMetrics.map((metric, i) => {
            const Icon = metric.icon;
            return (
              <motion.div
                key={metric.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.28 + i * 0.07 }}
                className={cn("cyber-card p-5 border", metric.borderColor)}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className={cn("p-2 rounded-lg border", metric.bgColor, metric.borderColor)}>
                    <Icon className={cn("w-5 h-5", metric.color)} />
                  </div>
                  <div className={cn("flex items-center gap-1 text-xs font-medium", metric.trendUp ? "text-red-400" : "text-green-400")}>
                    {metric.trendUp ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                    {metric.trend}
                  </div>
                </div>
                <div className={cn("text-2xl font-black mb-1", metric.color)}>
                  <AnimatedNumber
                    value={typeof metric.value === "number" ? metric.value : parseFloat(String(metric.value))}
                    suffix={metric.unit || ""}
                  />
                </div>
                <div className="text-xs text-muted-foreground">{metric.label}</div>
              </motion.div>
            );
          })}
        </div>

        {/* ── Charts Row 1 ── */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
          {/* Incidents Over Time - AreaChart */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="xl:col-span-2 cyber-card p-5 border border-border"
          >
            <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
              <Activity className="w-4 h-4 text-primary" /> Incidents Over Time
              <span className="text-xs text-muted-foreground font-normal">— {dateRange}</span>
            </h3>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={timeSeriesData}>
                <defs>
                  <linearGradient id="incidentGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#00d4ff" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="resolvedGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={{ stroke: "#1f2937" }} />
                <YAxis tick={{ fill: "#64748b", fontSize: 10 }} axisLine={{ stroke: "#1f2937" }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: 11, color: "#64748b" }} />
                <Area type="monotone" dataKey="incidents" stroke="#00d4ff" strokeWidth={2} fill="url(#incidentGrad)" name="Incidents" dot={false} />
                <Area type="monotone" dataKey="resolved" stroke="#10b981" strokeWidth={2} fill="url(#resolvedGrad)" name="Resolved" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </motion.div>

          {/* Attack Type Distribution - Donut */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.35 }}
            className="cyber-card p-5 border border-border"
          >
            <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
              <Target className="w-4 h-4 text-primary" /> Attack Types
            </h3>
            <ResponsiveContainer width="100%" height={150}>
              <PieChart>
                <Pie
                  data={ATTACK_TYPE_DATA}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={68}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {ATTACK_TYPE_DATA.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: "#111827", border: "1px solid #1f2937", borderRadius: "6px", fontSize: 11, color: "#e2e8f0" }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-1.5 mt-2">
              {ATTACK_TYPE_DATA.map((item) => (
                <div key={item.name} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full shrink-0" style={{ background: item.color }} />
                    <span className="text-muted-foreground">{item.name}</span>
                  </div>
                  <span className="font-mono font-medium text-foreground">{item.value}%</span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* ── Charts Row 1b — Severity Heatmap ── */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="xl:col-span-1 cyber-card p-5 border border-border"
          >
            <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" /> Severity Heatmap
            </h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={filteredSeverityData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
                <XAxis type="number" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={{ stroke: "#1f2937" }} />
                <YAxis dataKey="severity" type="category" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={{ stroke: "#1f2937" }} width={55} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} name="Count">
                  {filteredSeverityData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </motion.div>

          {/* MITRE Techniques */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.45 }}
            className="xl:col-span-2 cyber-card p-5 border border-border"
          >
            <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
              <Shield className="w-4 h-4 text-purple-400" /> Top 10 MITRE ATT&amp;CK Techniques
            </h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={MITRE_DATA} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
                <XAxis type="number" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={{ stroke: "#1f2937" }} />
                <YAxis
                  dataKey="technique"
                  type="category"
                  tick={{ fill: "#64748b", fontSize: 9 }}
                  axisLine={{ stroke: "#1f2937" }}
                  width={120}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: "#111827", border: "1px solid #1f2937", borderRadius: "6px", fontSize: 11, color: "#e2e8f0" }}
                />
                <Bar dataKey="count" fill="#7c3aed" radius={[0, 4, 4, 0]} name="Occurrences" />
              </BarChart>
            </ResponsiveContainer>
          </motion.div>
        </div>

        {/* ── Risky Assets Table ── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="cyber-card border border-border overflow-hidden"
        >
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
                  <motion.tr
                    key={asset.ip}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.55 + i * 0.05 }}
                    className="hover:bg-muted/30 transition-colors"
                  >
                    <td className="px-5 py-3 font-mono text-xs text-primary">{asset.ip}</td>
                    <td className="px-5 py-3 text-foreground">{asset.hostname}</td>
                    <td className="px-5 py-3">
                      <span className="font-mono font-bold text-foreground">{asset.incident_count}</span>
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                          <div
                            className={cn("h-full rounded-full", {
                              "bg-red-500": asset.risk_score >= 80,
                              "bg-orange-500": asset.risk_score >= 60 && asset.risk_score < 80,
                              "bg-amber-500": asset.risk_score >= 40 && asset.risk_score < 60,
                              "bg-green-500": asset.risk_score < 40,
                            })}
                            style={{ width: `${asset.risk_score}%` }}
                          />
                        </div>
                        <span className={cn("text-xs font-mono font-bold", {
                          "text-red-400": asset.risk_score >= 80,
                          "text-orange-400": asset.risk_score >= 60 && asset.risk_score < 80,
                          "text-amber-400": asset.risk_score >= 40 && asset.risk_score < 60,
                          "text-green-400": asset.risk_score < 40,
                        })}>
                          {asset.risk_score}
                        </span>
                      </div>
                    </td>
                    <td className="px-5 py-3 text-xs text-muted-foreground">{asset.last_seen}</td>
                    <td className="px-5 py-3">
                      <span className={cn("text-xs font-semibold capitalize", SEVERITY_COLORS[asset.severity])}>
                        {asset.severity}
                      </span>
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
