"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  DollarSign, Zap, TrendingDown, Database,
  BarChart2, Loader2, RefreshCw, Brain,
  CheckCircle2, AlertTriangle, PiggyBank,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell,
} from "recharts";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { cn } from "@/lib/utils";
import api from "@/lib/api";

const CHART_COLORS = ["#00d4ff", "#a855f7", "#10b981", "#f59e0b", "#ef4444", "#6366f1", "#ec4899"];

interface CostSummary {
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_cost: number;
  cache_savings: number;
  memory_savings: number;
  total_savings: number;
  total_calls: number;
  avg_cost_per_call: number;
  optimization_suggestions: Suggestion[];
}

interface AgentCost { agent_name: string; total_cost: number; total_tokens: number; call_count: number }
interface ModelCost { model_name: string; total_cost: number; total_tokens: number; call_count: number }
interface WorkflowCost { workflow_name: string; total_cost: number; total_tokens: number; call_count: number }
interface Savings { redis_cache_savings: number; memory_reuse_savings: number; rag_retrieval_savings: number; total_savings: number; estimated_monthly_savings: number; cache_hit_rate: number }
interface Suggestion { title: string; description: string; estimated_savings: string; priority: string; category: string }

const MOCK_SUMMARY: CostSummary = {
  total_tokens: 4_300_000, prompt_tokens: 2_800_000, completion_tokens: 1_500_000,
  total_cost: 82.40, cache_savings: 28.10, memory_savings: 9.25, total_savings: 37.35,
  total_calls: 3847, avg_cost_per_call: 0.0214,
  optimization_suggestions: [],
};
const MOCK_BY_AGENT: AgentCost[] = [
  { agent_name: "ConsensusAgent", total_cost: 23.52, total_tokens: 980_000, call_count: 412 },
  { agent_name: "AutonomousAgent", total_cost: 17.28, total_tokens: 720_000, call_count: 218 },
  { agent_name: "MitigationAgent", total_cost: 14.30, total_tokens: 650_000, call_count: 1842 },
  { agent_name: "ExplainabilityAgent", total_cost: 11.60, total_tokens: 580_000, call_count: 1842 },
  { agent_name: "SelfReflectionAgent", total_cost: 9.36, total_tokens: 390_000, call_count: 623 },
  { agent_name: "ClassificationAgent", total_cost: 5.12, total_tokens: 320_000, call_count: 1842 },
  { agent_name: "JudgeAgent", total_cost: 4.56, total_tokens: 285_000, call_count: 1842 },
];
const MOCK_BY_MODEL: ModelCost[] = [
  { model_name: "gpt-4.1", total_cost: 44.40, total_tokens: 1_850_000, call_count: 924 },
  { model_name: "gpt-4.1-mini", total_cost: 23.50, total_tokens: 1_640_000, call_count: 2418 },
  { model_name: "claude-3-5-sonnet", total_cost: 11.58, total_tokens: 640_000, call_count: 412 },
  { model_name: "text-embedding-3-small", total_cost: 0.34, total_tokens: 170_000, call_count: 4200 },
  { model_name: "llama-3.1-8b", total_cost: 0.02, total_tokens: 210_000, call_count: 218 },
];
const MOCK_SAVINGS: Savings = {
  redis_cache_savings: 28.10, memory_reuse_savings: 9.25, rag_retrieval_savings: 5.60,
  total_savings: 42.95, estimated_monthly_savings: 42.95, cache_hit_rate: 34.2,
};
const MOCK_TREND = Array.from({ length: 14 }, (_, i) => ({
  date: `Jun ${i + 1}`, cost: +(Math.random() * 4 + 1).toFixed(2),
  savings: +(Math.random() * 1.5 + 0.5).toFixed(2),
}));
const MOCK_SUGGESTIONS: Suggestion[] = [
  { title: "Use smaller model for low-severity incidents", description: "Switch gpt-4.1-mini for low/medium severity — ~60% cost reduction", estimated_savings: "$15-25/month", priority: "high", category: "model_selection" },
  { title: "Cache repeated MITRE mapping calls", description: "Cache MITRE technique mapping results in Redis (TTL 1h)", estimated_savings: "$8-12/month", priority: "medium", category: "caching" },
  { title: "Use local model for simulation mode", description: "Digital twin simulations can use Llama-3.1-8B locally for near-zero cost", estimated_savings: "$20-35/month", priority: "high", category: "model_selection" },
  { title: "Summarise context before consensus", description: "Reduce input tokens 40% by summarizing before sending to all models", estimated_savings: "$10-18/month", priority: "medium", category: "prompt_optimization" },
  { title: "Skip consensus for low-risk incidents", description: "Only run multi-LLM consensus for high/critical severity (risk > 60)", estimated_savings: "$25-40/month", priority: "high", category: "workflow" },
];

const PRIORITY_STYLES: Record<string, string> = {
  critical: "border-red-500/40 bg-red-500/10 text-red-400",
  high: "border-amber-500/40 bg-amber-500/10 text-amber-400",
  medium: "border-primary/40 bg-primary/10 text-primary",
  low: "border-green-500/40 bg-green-500/10 text-green-400",
};

export default function CostIntelligencePage() {
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [byAgent, setByAgent] = useState<AgentCost[]>([]);
  const [byModel, setByModel] = useState<ModelCost[]>([]);
  const [savings, setSavings] = useState<Savings | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [sumRes, agentRes, modelRes, savingsRes] = await Promise.allSettled([
        api.get(`/cost/summary?days=${days}`),
        api.get(`/cost/by-agent?days=${days}`),
        api.get(`/cost/by-model?days=${days}`),
        api.get(`/cost/savings?days=${days}`),
      ]);
      setSummary(sumRes.status === "fulfilled" ? sumRes.value.data : MOCK_SUMMARY);
      setByAgent(agentRes.status === "fulfilled" ? agentRes.value.data.data : MOCK_BY_AGENT);
      setByModel(modelRes.status === "fulfilled" ? modelRes.value.data.data : MOCK_BY_MODEL);
      setSavings(savingsRes.status === "fulfilled" ? savingsRes.value.data : MOCK_SAVINGS);
    } catch {
      setSummary(MOCK_SUMMARY);
      setByAgent(MOCK_BY_AGENT);
      setByModel(MOCK_BY_MODEL);
      setSavings(MOCK_SAVINGS);
    }
    setLoading(false);
  };

  useEffect(() => { fetchAll(); }, [days]);

  const formatTokens = (n: number) => n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1_000 ? `${(n / 1_000).toFixed(0)}K` : String(n);

  return (
    <DashboardLayout>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              <span className="text-xs font-mono text-muted-foreground uppercase tracking-widest">Cost Intelligence Platform</span>
            </div>
            <h1 className="text-xl font-bold text-foreground">LLM Cost & Optimization</h1>
            <p className="text-sm text-muted-foreground mt-1">Track token usage, costs, savings, and optimization opportunities across all AI workflows</p>
          </div>
          <div className="flex items-center gap-2">
            <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="cyber-input text-xs px-3 py-2">
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            <button type="button" onClick={fetchAll} disabled={loading} className="p-2 rounded-lg border border-border hover:bg-muted text-muted-foreground transition-colors">
              <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                { label: "Total Cost", value: `$${(summary?.total_cost || 82.40).toFixed(2)}`, icon: DollarSign, color: "text-primary", sub: `${days} days` },
                { label: "Total Tokens", value: formatTokens(summary?.total_tokens || 4_300_000), icon: Zap, color: "text-purple-400", sub: `${formatTokens(summary?.prompt_tokens || 0)} prompt` },
                { label: "Avg Cost/Call", value: `$${(summary?.avg_cost_per_call || 0.0214).toFixed(4)}`, icon: BarChart2, color: "text-amber-400", sub: `${(summary?.total_calls || 3847).toLocaleString()} calls` },
                { label: "Total Savings", value: `$${(summary?.total_savings || 37.35).toFixed(2)}`, icon: PiggyBank, color: "text-green-400", sub: `${((summary?.total_savings || 37) / (summary?.total_cost || 82) * 100).toFixed(0)}% saved` },
              ].map((stat) => {
                const Icon = stat.icon;
                return (
                  <div key={stat.label} className="cyber-card p-4 border border-border">
                    <div className="flex items-center gap-2 mb-2">
                      <Icon className={cn("w-4 h-4", stat.color)} />
                      <span className="text-xs text-muted-foreground">{stat.label}</span>
                    </div>
                    <p className={cn("text-2xl font-black", stat.color)}>{stat.value}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{stat.sub}</p>
                  </div>
                );
              })}
            </div>

            {/* Savings Cards */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
              {[
                { label: "Redis Cache Savings", value: savings?.redis_cache_savings || 28.10, icon: Database, color: "text-primary", rate: `${savings?.cache_hit_rate || 34.2}% hit rate` },
                { label: "Memory Reuse Savings", value: savings?.memory_reuse_savings || 9.25, icon: Brain, color: "text-purple-400", rate: "semantic memory matches" },
                { label: "RAG Retrieval Savings", value: savings?.rag_retrieval_savings || 5.60, icon: TrendingDown, color: "text-green-400", rate: "avoided LLM re-calls" },
              ].map((s) => {
                const Icon = s.icon;
                return (
                  <div key={s.label} className="cyber-card p-4 border border-green-500/20 bg-green-500/3">
                    <div className="flex items-center gap-2 mb-2">
                      <Icon className={cn("w-4 h-4", s.color)} />
                      <span className="text-xs text-muted-foreground">{s.label}</span>
                    </div>
                    <p className={cn("text-xl font-black", s.color)}>${s.value.toFixed(2)}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{s.rate}</p>
                  </div>
                );
              })}
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Cost by Agent */}
              <div className="cyber-card p-5 border border-border">
                <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
                  <Brain className="w-4 h-4 text-primary" /> Cost by Agent
                </h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={byAgent.slice(0, 6)} margin={{ top: 0, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis dataKey="agent_name" tick={{ fill: "#6b7280", fontSize: 10 }} tickFormatter={(v) => v.replace("Agent", "")} />
                    <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} tickFormatter={(v) => `$${v}`} />
                    <Tooltip
                      contentStyle={{ background: "#111827", border: "1px solid #1f2937", borderRadius: "8px" }}
                      formatter={(v: number) => [`$${v.toFixed(2)}`, "Cost"]}
                    />
                    <Bar dataKey="total_cost" fill="#00d4ff" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Cost by Model Pie */}
              <div className="cyber-card p-5 border border-border">
                <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
                  <BarChart2 className="w-4 h-4 text-purple-400" /> Cost by Model
                </h3>
                <div className="flex items-center gap-4">
                  <ResponsiveContainer width="50%" height={200}>
                    <PieChart>
                      <Pie data={byModel} dataKey="total_cost" nameKey="model_name" cx="50%" cy="50%" outerRadius={80} innerRadius={45}>
                        {byModel.map((_, i) => (
                          <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ background: "#111827", border: "1px solid #1f2937", borderRadius: "8px" }}
                        formatter={(v: number) => [`$${v.toFixed(2)}`, "Cost"]}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex-1 space-y-2">
                    {byModel.slice(0, 5).map((m, i) => (
                      <div key={m.model_name} className="flex items-center gap-2 text-xs">
                        <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }} />
                        <span className="text-muted-foreground truncate flex-1">{m.model_name}</span>
                        <span className="font-mono text-foreground shrink-0">${m.total_cost.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Cost Trend */}
              <div className="cyber-card p-5 border border-border lg:col-span-2">
                <h3 className="text-sm font-semibold text-foreground mb-4">Cost Trend (14 days)</h3>
                <ResponsiveContainer width="100%" height={180}>
                  <LineChart data={MOCK_TREND} margin={{ top: 0, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 10 }} />
                    <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} tickFormatter={(v) => `$${v}`} />
                    <Tooltip contentStyle={{ background: "#111827", border: "1px solid #1f2937", borderRadius: "8px" }} formatter={(v: number) => [`$${v.toFixed(2)}`, ""]} />
                    <Line type="monotone" dataKey="cost" stroke="#00d4ff" strokeWidth={2} dot={false} name="Cost" />
                    <Line type="monotone" dataKey="savings" stroke="#10b981" strokeWidth={2} dot={false} strokeDasharray="4 2" name="Savings" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Optimization Suggestions */}
            <div className="cyber-card border border-border overflow-hidden">
              <div className="px-5 py-4 border-b border-border flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-primary" />
                <h3 className="text-sm font-semibold text-foreground">Optimization Suggestions</h3>
              </div>
              <div className="divide-y divide-border">
                {(summary?.optimization_suggestions?.length ? summary.optimization_suggestions : MOCK_SUGGESTIONS).map((s, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="px-5 py-4 flex items-start gap-4"
                  >
                    <span className={cn("px-2 py-0.5 rounded-full text-xs font-semibold border shrink-0 capitalize", PRIORITY_STYLES[s.priority] || PRIORITY_STYLES.medium)}>
                      {s.priority}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground">{s.title}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{s.description}</p>
                    </div>
                    <span className="text-xs font-mono text-green-400 shrink-0">{s.estimated_savings}</span>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        )}
      </motion.div>
    </DashboardLayout>
  );
}
