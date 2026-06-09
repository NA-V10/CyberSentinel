"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  GitBranch, TrendingUp, FileText, Shield, Search, Target,
  MessageSquare, BookOpen, Clock, Wrench, Play, X, Loader2,
  CheckCircle2, AlertCircle, Activity
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import api from "@/lib/api";
import { toast } from "sonner";

const TOOL_ICONS: Record<string, React.ElementType> = {
  graph_query: GitBranch,
  risk_score: TrendingUp,
  report_generator: FileText,
  guardrail_check: Shield,
  threat_intel_lookup: Search,
  mitre_mapper: Target,
  similar_incident_search: Search,
  feedback_store: MessageSquare,
  playbook_generator: BookOpen,
  sla_tracker: Clock,
};

const CATEGORY_COLORS: Record<string, string> = {
  "Graph Intelligence": "text-purple-400 bg-purple-500/10 border-purple-500/20",
  "Risk Assessment": "text-orange-400 bg-orange-500/10 border-orange-500/20",
  "Reporting": "text-blue-400 bg-blue-500/10 border-blue-500/20",
  "Security": "text-red-400 bg-red-500/10 border-red-500/20",
  "Intelligence": "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
  "Classification": "text-primary bg-primary/10 border-primary/20",
  "Search": "text-green-400 bg-green-500/10 border-green-500/20",
  "Learning": "text-pink-400 bg-pink-500/10 border-pink-500/20",
  "Response": "text-amber-400 bg-amber-500/10 border-amber-500/20",
  "Operations": "text-teal-400 bg-teal-500/10 border-teal-500/20",
};

interface MCPTool {
  name: string;
  display_name: string;
  description: string;
  category: string;
  status: string;
  input_schema: Record<string, unknown>;
  last_used_at: string;
  total_calls: number;
  avg_response_ms: number;
}

interface TestResult {
  tool_name: string;
  output: unknown;
  response_time_ms: number;
  status: string;
  error?: string;
}

const SAMPLE_INPUTS: Record<string, Record<string, unknown>> = {
  risk_score: { severity: "high", attack_type: "Brute Force", source_ip: "185.220.101.47" },
  mitre_mapper: { attack_type: "Phishing", incident_text: "Spearphishing email targeting HR department" },
  threat_intel_lookup: { ip: "185.220.101.47" },
  playbook_generator: { attack_type: "Malware", severity: "critical" },
  guardrail_check: { text: "Analyze this suspicious SSH brute force incident from external IP" },
  graph_query: { attack_type: "Brute Force", depth: 2 },
  similar_incident_search: { query: "SSH brute force from external IP", limit: 5 },
  sla_tracker: { incident_id: "demo-id", severity: "high" },
  feedback_store: { rating: 4, comment: "Mitigation steps were helpful", mitigation_worked: true },
  report_generator: { incident_id: "demo-id", format: "markdown" },
};

export default function MCPToolsPage() {
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [loading, setLoading] = useState(true);
  const [testingTool, setTestingTool] = useState<string | null>(null);
  const [testModal, setTestModal] = useState<{ tool: MCPTool; input: string } | null>(null);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [testLoading, setTestLoading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get("/mcp/tools");
        setTools(res.data.tools || []);
      } catch {
        // Fallback mock data
        setTools(FALLBACK_TOOLS);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const openTestModal = (tool: MCPTool) => {
    const sampleInput = SAMPLE_INPUTS[tool.name] || {};
    setTestResult(null);
    setTestModal({ tool, input: JSON.stringify(sampleInput, null, 2) });
  };

  const runTest = async () => {
    if (!testModal) return;
    setTestLoading(true);
    setTestResult(null);
    try {
      let input: Record<string, unknown> = {};
      try { input = JSON.parse(testModal.input); } catch { /* invalid json */ }
      const res = await api.post(`/mcp/tools/${testModal.tool.name}/test`, { input });
      setTestResult(res.data);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setTestResult({
        tool_name: testModal.tool.name,
        output: { error: axiosErr?.response?.data?.detail || "Request failed" },
        response_time_ms: 0,
        status: "error",
        error: axiosErr?.response?.data?.detail || "Request failed",
      });
    } finally {
      setTestLoading(false);
    }
  };

  const activeTotalCalls = tools.reduce((s, t) => s + (t.total_calls || 0), 0);

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
              <Wrench className="w-6 h-6 text-primary" />
            </div>
            MCP Tool Marketplace
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Available tools for the CyberSentinel AI agent pipeline
          </p>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[
          { label: "Active Tools", value: tools.filter(t => t.status === "active").length, icon: CheckCircle2, color: "text-green-400" },
          { label: "Total API Calls", value: activeTotalCalls.toLocaleString(), icon: Activity, color: "text-primary" },
          { label: "Avg Response", value: tools.length ? `${Math.round(tools.reduce((s, t) => s + (t.avg_response_ms || 0), 0) / tools.length)}ms` : "—", icon: Clock, color: "text-purple-400" },
        ].map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="cyber-card p-4 border border-border"
          >
            <div className="flex items-center gap-3">
              <stat.icon className={`w-5 h-5 ${stat.color}`} />
              <div>
                <div className="text-xl font-bold text-foreground">{stat.value}</div>
                <div className="text-xs text-muted-foreground">{stat.label}</div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Tools grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="cyber-card p-5 border border-border animate-pulse h-52" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {tools.map((tool, i) => {
            const Icon = TOOL_ICONS[tool.name] || Wrench;
            const catColor = CATEGORY_COLORS[tool.category] || "text-primary bg-primary/10 border-primary/20";
            return (
              <motion.div
                key={tool.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="cyber-card p-5 border border-border flex flex-col gap-4 group hover:border-primary/40 transition-colors"
              >
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
                      <Icon className="w-5 h-5 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-foreground text-sm">{tool.display_name}</h3>
                      <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${catColor}`}>
                        {tool.category}
                      </span>
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${
                    tool.status === "active"
                      ? "text-green-400 bg-green-500/10 border-green-500/20"
                      : "text-muted-foreground bg-muted border-border"
                  }`}>
                    {tool.status === "active" ? "● Active" : "Inactive"}
                  </span>
                </div>

                {/* Description */}
                <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
                  {tool.description}
                </p>

                {/* Stats */}
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span>{tool.total_calls?.toLocaleString() || 0} calls</span>
                  <span>~{tool.avg_response_ms || 0}ms</span>
                  <span>Last: {tool.last_used_at ? new Date(tool.last_used_at).toLocaleDateString() : "—"}</span>
                </div>

                {/* Test button */}
                <button
                  onClick={() => openTestModal(tool)}
                  className="flex items-center justify-center gap-2 w-full py-2 px-3 rounded-md border border-primary/30 bg-primary/5 text-primary text-xs font-medium hover:bg-primary/10 transition-colors"
                >
                  <Play className="w-3.5 h-3.5" />
                  Test Tool
                </button>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Test Modal */}
      <AnimatePresence>
        {testModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={(e) => e.target === e.currentTarget && setTestModal(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="cyber-card border border-border w-full max-w-2xl max-h-[85vh] overflow-y-auto p-6"
            >
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-lg font-bold text-foreground">
                  Test: <span className="text-primary">{testModal.tool.display_name}</span>
                </h2>
                <button onClick={() => setTestModal(null)} className="text-muted-foreground hover:text-foreground">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">Input JSON</label>
                  <textarea
                    value={testModal.input}
                    onChange={e => setTestModal(prev => prev ? { ...prev, input: e.target.value } : null)}
                    className="cyber-input w-full h-32 font-mono text-xs resize-none"
                    placeholder="{}"
                  />
                </div>

                <button
                  onClick={runTest}
                  disabled={testLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-primary text-background rounded-md text-sm font-semibold hover:bg-primary/90 transition-all disabled:opacity-50"
                >
                  {testLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  {testLoading ? "Running..." : "Run Test"}
                </button>

                {testResult && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      {testResult.status === "success"
                        ? <CheckCircle2 className="w-4 h-4 text-green-400" />
                        : <AlertCircle className="w-4 h-4 text-red-400" />
                      }
                      <span className={`text-xs font-medium ${testResult.status === "success" ? "text-green-400" : "text-red-400"}`}>
                        {testResult.status === "success" ? "Success" : "Error"} — {testResult.response_time_ms}ms
                      </span>
                    </div>
                    <pre className="bg-muted/50 border border-border rounded-lg p-3 text-xs text-foreground overflow-auto max-h-64 font-mono whitespace-pre-wrap">
                      {JSON.stringify(testResult.output, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </DashboardLayout>
  );
}

const FALLBACK_TOOLS: MCPTool[] = [
  { name: "graph_query", display_name: "Graph Query", description: "Query Neo4j knowledge graph for threat relationships.", category: "Graph Intelligence", status: "active", input_schema: {}, last_used_at: "2024-01-15T14:23:00Z", total_calls: 1247, avg_response_ms: 45 },
  { name: "risk_score", display_name: "Risk Score Calculator", description: "Calculate explainable risk scores (0-100).", category: "Risk Assessment", status: "active", input_schema: {}, last_used_at: "2024-01-15T14:45:00Z", total_calls: 983, avg_response_ms: 210 },
  { name: "mitre_mapper", display_name: "MITRE ATT&CK Mapper", description: "Map attacks to MITRE ATT&CK techniques.", category: "Classification", status: "active", input_schema: {}, last_used_at: "2024-01-15T14:30:00Z", total_calls: 1876, avg_response_ms: 340 },
  { name: "threat_intel_lookup", display_name: "Threat Intel Lookup", description: "Enrich IPs, domains, and hashes.", category: "Intelligence", status: "active", input_schema: {}, last_used_at: "2024-01-15T14:55:00Z", total_calls: 2341, avg_response_ms: 95 },
  { name: "playbook_generator", display_name: "Playbook Generator", description: "Generate incident response playbooks.", category: "Response", status: "active", input_schema: {}, last_used_at: "2024-01-15T10:30:00Z", total_calls: 445, avg_response_ms: 520 },
  { name: "guardrail_check", display_name: "Guardrail Validator", description: "Validate inputs against security policies.", category: "Security", status: "active", input_schema: {}, last_used_at: "2024-01-15T15:00:00Z", total_calls: 8921, avg_response_ms: 8 },
  { name: "sla_tracker", display_name: "SLA Tracker", description: "Track SLA deadlines per severity.", category: "Operations", status: "active", input_schema: {}, last_used_at: "2024-01-15T14:00:00Z", total_calls: 1123, avg_response_ms: 30 },
  { name: "feedback_store", display_name: "Feedback Store", description: "Store analyst feedback for continuous learning.", category: "Learning", status: "active", input_schema: {}, last_used_at: "2024-01-15T11:20:00Z", total_calls: 678, avg_response_ms: 25 },
  { name: "similar_incident_search", display_name: "Similar Incident Search", description: "Find semantically similar historical incidents.", category: "Search", status: "active", input_schema: {}, last_used_at: "2024-01-15T13:45:00Z", total_calls: 3102, avg_response_ms: 180 },
  { name: "report_generator", display_name: "Report Generator", description: "Generate reports in Markdown or PDF.", category: "Reporting", status: "active", input_schema: {}, last_used_at: "2024-01-15T12:10:00Z", total_calls: 456, avg_response_ms: 1200 },
];
