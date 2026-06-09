"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  Shield,
  AlertTriangle,
  Clock,
  Activity,
  TrendingUp,
  TrendingDown,
  ArrowRight,
  RefreshCw,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { SeverityBadge } from "@/components/incidents/SeverityBadge";
import { formatRelativeTime } from "@/lib/utils";

// Mock data
const incidentTrendData = [
  { date: "Jun 1", incidents: 12, resolved: 10 },
  { date: "Jun 2", incidents: 19, resolved: 15 },
  { date: "Jun 3", incidents: 8, resolved: 8 },
  { date: "Jun 4", incidents: 25, resolved: 18 },
  { date: "Jun 5", incidents: 17, resolved: 14 },
  { date: "Jun 6", incidents: 22, resolved: 20 },
  { date: "Jun 7", incidents: 14, resolved: 12 },
];

const attackTypeData = [
  { name: "Ransomware", value: 28, color: "#ef4444" },
  { name: "Phishing", value: 22, color: "#f97316" },
  { name: "DDoS", value: 18, color: "#f59e0b" },
  { name: "SQL Injection", value: 15, color: "#7c3aed" },
  { name: "Zero-Day", value: 10, color: "#00d4ff" },
  { name: "Other", value: 7, color: "#64748b" },
];

const severityData = [
  { severity: "Critical", count: 8, fill: "#ef4444" },
  { severity: "High", count: 23, fill: "#f97316" },
  { severity: "Medium", count: 45, fill: "#f59e0b" },
  { severity: "Low", count: 67, fill: "#10b981" },
];

const recentIncidents = [
  {
    id: "INC-001",
    description: "Ransomware detected on finance servers — encrypted 200 files",
    severity: "critical",
    threat_class: "Ransomware",
    created_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    status: "active",
  },
  {
    id: "INC-002",
    description: "Suspicious SSH brute force from IP 192.168.1.45",
    severity: "high",
    threat_class: "Brute Force",
    created_at: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
    status: "analyzing",
  },
  {
    id: "INC-003",
    description: "SQL injection attempt on customer portal API endpoint",
    severity: "medium",
    threat_class: "SQL Injection",
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    status: "resolved",
  },
  {
    id: "INC-004",
    description: "Phishing email campaign targeting HR department",
    severity: "high",
    threat_class: "Phishing",
    created_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    status: "resolved",
  },
  {
    id: "INC-005",
    description: "DDoS attack on public API — 50K requests/sec",
    severity: "critical",
    threat_class: "DDoS",
    created_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    status: "resolved",
  },
];

const stats = [
  {
    label: "Total Incidents",
    value: "143",
    trend: "+12%",
    trendUp: true,
    icon: Shield,
    color: "text-primary",
    bgColor: "bg-primary/10",
    borderColor: "border-primary/20",
  },
  {
    label: "Critical Alerts",
    value: "8",
    trend: "-3%",
    trendUp: false,
    icon: AlertTriangle,
    color: "text-red-400",
    bgColor: "bg-red-500/10",
    borderColor: "border-red-500/20",
  },
  {
    label: "Avg Response Time",
    value: "1.8s",
    trend: "-0.4s",
    trendUp: false,
    icon: Clock,
    color: "text-green-400",
    bgColor: "bg-green-500/10",
    borderColor: "border-green-500/20",
  },
  {
    label: "Active Sessions",
    value: "24",
    trend: "+5",
    trendUp: true,
    icon: Activity,
    color: "text-purple-400",
    bgColor: "bg-purple-500/10",
    borderColor: "border-purple-500/20",
  },
];

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; color: string }>; label?: string }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-card border border-border rounded-lg p-3 text-xs shadow-xl">
        <p className="text-muted-foreground mb-2">{label}</p>
        {payload.map((entry, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full" style={{ background: entry.color }} />
            <span className="text-foreground">
              {entry.name}: {entry.value}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function DashboardPage() {
  const router = useRouter();
  const [quickAnalysis, setQuickAnalysis] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await new Promise((r) => setTimeout(r, 1000));
    setIsRefreshing(false);
  };

  const handleQuickAnalysis = () => {
    if (quickAnalysis.trim()) {
      router.push(
        `/incidents?description=${encodeURIComponent(quickAnalysis)}`
      );
    }
  };

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Security Dashboard
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Real-time overview of your security posture
          </p>
        </div>
        <button
          onClick={handleRefresh}
          className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border hover:bg-muted text-muted-foreground hover:text-foreground text-sm transition-colors"
        >
          <RefreshCw
            className={`w-4 h-4 ${isRefreshing ? "animate-spin" : ""}`}
          />
          Refresh
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: i * 0.08 }}
            className={`cyber-card p-5 border ${stat.borderColor}`}
          >
            <div className="flex items-center justify-between mb-3">
              <div
                className={`p-2 rounded-lg ${stat.bgColor} border ${stat.borderColor}`}
              >
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
              <div
                className={`flex items-center gap-1 text-xs font-medium ${
                  stat.trendUp ? "text-green-400" : "text-red-400"
                }`}
              >
                {stat.trendUp ? (
                  <TrendingUp className="w-3.5 h-3.5" />
                ) : (
                  <TrendingDown className="w-3.5 h-3.5" />
                )}
                {stat.trend}
              </div>
            </div>
            <div className="text-2xl font-bold text-foreground mb-1">
              {stat.value}
            </div>
            <div className="text-xs text-muted-foreground">{stat.label}</div>
          </motion.div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-8">
        {/* Incidents Over Time */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="xl:col-span-2 cyber-card p-5 border border-border"
        >
          <h3 className="text-sm font-semibold text-foreground mb-4">
            Incidents Over Time
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={incidentTrendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis
                dataKey="date"
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={{ stroke: "#1f2937" }}
              />
              <YAxis
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={{ stroke: "#1f2937" }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: 11, color: "#64748b" }}
              />
              <Line
                type="monotone"
                dataKey="incidents"
                stroke="#00d4ff"
                strokeWidth={2}
                dot={{ fill: "#00d4ff", r: 3 }}
                activeDot={{ r: 5 }}
                name="Total Incidents"
              />
              <Line
                type="monotone"
                dataKey="resolved"
                stroke="#10b981"
                strokeWidth={2}
                dot={{ fill: "#10b981", r: 3 }}
                activeDot={{ r: 5 }}
                name="Resolved"
              />
            </LineChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Attack Type Distribution */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="cyber-card p-5 border border-border"
        >
          <h3 className="text-sm font-semibold text-foreground mb-4">
            Attack Types
          </h3>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie
                data={attackTypeData}
                cx="50%"
                cy="50%"
                innerRadius={45}
                outerRadius={70}
                paddingAngle={3}
                dataKey="value"
              >
                {attackTypeData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "#111827",
                  border: "1px solid #1f2937",
                  borderRadius: "6px",
                  fontSize: 11,
                  color: "#e2e8f0",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1.5 mt-2">
            {attackTypeData.map((item) => (
              <div
                key={item.name}
                className="flex items-center justify-between text-xs"
              >
                <div className="flex items-center gap-2">
                  <div
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ background: item.color }}
                  />
                  <span className="text-muted-foreground">{item.name}</span>
                </div>
                <span className="text-foreground font-medium">
                  {item.value}%
                </span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Severity Breakdown + Recent Incidents */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-8">
        {/* Severity Bar Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="cyber-card p-5 border border-border"
        >
          <h3 className="text-sm font-semibold text-foreground mb-4">
            Severity Breakdown
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={severityData} layout="vertical">
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#1f2937"
                horizontal={false}
              />
              <XAxis
                type="number"
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={{ stroke: "#1f2937" }}
              />
              <YAxis
                dataKey="severity"
                type="category"
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={{ stroke: "#1f2937" }}
                width={55}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} name="Count">
                {severityData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Recent Incidents Table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="xl:col-span-2 cyber-card border border-border overflow-hidden"
        >
          <div className="flex items-center justify-between p-5 border-b border-border">
            <h3 className="text-sm font-semibold text-foreground">
              Recent Incidents
            </h3>
            <button
              onClick={() => router.push("/incidents")}
              className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
            >
              View All <ArrowRight className="w-3 h-3" />
            </button>
          </div>
          <div className="divide-y divide-border">
            {recentIncidents.map((incident) => (
              <div
                key={incident.id}
                className="flex items-center gap-3 p-4 hover:bg-muted/30 transition-colors cursor-pointer"
                onClick={() => router.push(`/incidents?id=${incident.id}`)}
              >
                <div className="shrink-0">
                  <SeverityBadge
                    severity={
                      incident.severity as
                        | "critical"
                        | "high"
                        | "medium"
                        | "low"
                    }
                    size="sm"
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground truncate">
                    {incident.description}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-purple-400">
                      {incident.threat_class}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {formatRelativeTime(incident.created_at)}
                    </span>
                  </div>
                </div>
                <div className="shrink-0">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full border font-medium ${
                      incident.status === "active"
                        ? "border-red-500/40 bg-red-500/10 text-red-400"
                        : incident.status === "analyzing"
                        ? "border-primary/40 bg-primary/10 text-primary"
                        : "border-green-500/40 bg-green-500/10 text-green-400"
                    }`}
                  >
                    {incident.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Quick Analysis */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.6 }}
        className="cyber-card border border-border p-5"
      >
        <h3 className="text-sm font-semibold text-foreground mb-3">
          Quick Incident Analysis
        </h3>
        <div className="flex gap-3">
          <input
            type="text"
            value={quickAnalysis}
            onChange={(e) => setQuickAnalysis(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleQuickAnalysis()}
            placeholder="Describe an incident quickly (e.g., 'Ransomware detected on prod servers...')"
            className="flex-1 cyber-input"
          />
          <button
            onClick={handleQuickAnalysis}
            disabled={!quickAnalysis.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-background rounded-md text-sm font-semibold hover:bg-primary/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-[0_0_15px_rgba(0,212,255,0.3)]"
          >
            Analyze
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </motion.div>
    </DashboardLayout>
  );
}
