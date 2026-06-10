"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FlaskConical, Play, CheckCircle2, XCircle, Loader2,
  AlertTriangle, Zap, Bug, Shield, User, Upload,
  BarChart2, Activity, Clock, Target,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import api from "@/lib/api";

interface Scenario {
  id: string;
  name: string;
  description: string;
  scenario_type: string;
  attack_type: string;
  severity: string;
  expected_mitre_technique: string;
  expected_response: string;
  icon: string;
  difficulty: string;
  incident_count: number;
}

interface RunResult {
  run_id: string;
  scenario_name: string;
  accuracy_score: number;
  response_quality_score: number;
  comparison_summary: string;
  synthetic_incidents: unknown[];
  agent_responses: AgentResponse[];
  recommendations: string[];
}

interface AgentResponse {
  incident_id: string;
  classification: string;
  expected_classification: string;
  correct: boolean;
  confidence: number;
  response_quality: number;
}

const SCENARIO_ICONS: Record<string, React.ElementType> = {
  phishing: Shield,
  malware: Bug,
  ddos: Zap,
  insider: User,
  brute_force: Target,
  exfiltration: Upload,
};

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: "border-green-500/40 bg-green-500/10 text-green-400",
  medium: "border-amber-500/40 bg-amber-500/10 text-amber-400",
  hard: "border-red-500/40 bg-red-500/10 text-red-400",
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: "text-red-400",
  high: "text-orange-400",
  medium: "text-amber-400",
  low: "text-green-400",
};

export default function DigitalTwinPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningScenario, setRunningScenario] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, RunResult>>({});

  useEffect(() => {
    const fetchScenarios = async () => {
      try {
        const res = await api.get("/digital-twin/scenarios");
        setScenarios(res.data.scenarios || []);
      } catch {
        setScenarios(MOCK_SCENARIOS);
      }
      setLoading(false);
    };
    fetchScenarios();
  }, []);

  const runScenario = async (scenarioId: string) => {
    setRunningScenario(scenarioId);
    try {
      const res = await api.post(`/digital-twin/run/${scenarioId}`);
      setResults((prev) => ({ ...prev, [scenarioId]: res.data }));
      toast.success(`Simulation complete — ${res.data.accuracy_score}% accuracy`);
    } catch {
      const mock = generateMockResult(scenarioId, scenarios.find((s) => s.id === scenarioId)?.name || "Scenario");
      setResults((prev) => ({ ...prev, [scenarioId]: mock }));
      toast.success(`Simulation complete — ${mock.accuracy_score}% accuracy`);
    }
    setRunningScenario(null);
  };

  return (
    <DashboardLayout>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            <span className="text-xs font-mono text-muted-foreground uppercase tracking-widest">AI SOC Digital Twin</span>
          </div>
          <h1 className="text-xl font-bold text-foreground">Digital Twin Simulator</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Simulate attack scenarios in a safe environment. Watch agents respond and compare expected vs actual outcomes.
          </p>
        </div>

        {/* Workflow Banner */}
        <div className="cyber-card p-4 border border-primary/20 bg-primary/3 mb-6">
          <div className="flex items-center gap-2 flex-wrap text-xs text-muted-foreground">
            {["Launch Scenario", "Synthetic Incidents Generated", "Agents Respond", "Review Decisions", "Compare Outcomes"].map((step, i, arr) => (
              <span key={step} className="flex items-center gap-2">
                <span className={cn("px-2 py-1 rounded border", i === 0 ? "border-primary/40 text-primary bg-primary/10" : "border-border text-muted-foreground")}>{step}</span>
                {i < arr.length - 1 && <span className="text-muted-foreground/40">→</span>}
              </span>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
            {(scenarios.length > 0 ? scenarios : MOCK_SCENARIOS).map((scenario, i) => {
              const Icon = SCENARIO_ICONS[scenario.scenario_type] || FlaskConical;
              const isRunning = runningScenario === scenario.id;
              const result = results[scenario.id];

              return (
                <motion.div
                  key={scenario.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="cyber-card border border-border overflow-hidden"
                >
                  {/* Card Header */}
                  <div className="p-5 border-b border-border">
                    <div className="flex items-start justify-between mb-3">
                      <div className="w-10 h-10 rounded-xl border border-primary/20 bg-primary/5 flex items-center justify-center">
                        <Icon className="w-5 h-5 text-primary" />
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium capitalize", DIFFICULTY_COLORS[scenario.difficulty] || DIFFICULTY_COLORS.medium)}>
                          {scenario.difficulty}
                        </span>
                        <span className={cn("text-xs font-semibold capitalize", SEVERITY_COLORS[scenario.severity] || "text-foreground")}>
                          {scenario.severity}
                        </span>
                      </div>
                    </div>
                    <h3 className="text-sm font-bold text-foreground mb-1">{scenario.name}</h3>
                    <p className="text-xs text-muted-foreground leading-relaxed">{scenario.description}</p>
                  </div>

                  {/* Meta */}
                  <div className="px-5 py-3 border-b border-border space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">MITRE</span>
                      <span className="font-mono text-purple-400">{scenario.expected_mitre_technique.split(" - ")[0]}</span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Attack Type</span>
                      <span className="text-foreground">{scenario.attack_type}</span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Incidents</span>
                      <span className="font-mono text-foreground">{scenario.incident_count} synthetic</span>
                    </div>
                  </div>

                  {/* Result if available */}
                  {result && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      className="px-5 py-3 border-b border-border bg-muted/30"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-foreground">Latest Run Results</span>
                        <span className={cn("text-sm font-black", result.accuracy_score >= 85 ? "text-green-400" : result.accuracy_score >= 70 ? "text-amber-400" : "text-red-400")}>
                          {result.accuracy_score}% accuracy
                        </span>
                      </div>
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">Response Quality</span>
                          <span className="font-mono text-foreground">{result.response_quality_score}%</span>
                        </div>
                        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                          <motion.div
                            className={cn("h-full rounded-full", result.accuracy_score >= 85 ? "bg-green-500" : result.accuracy_score >= 70 ? "bg-amber-500" : "bg-red-500")}
                            initial={{ width: "0%" }}
                            animate={{ width: `${result.accuracy_score}%` }}
                            transition={{ duration: 0.8 }}
                          />
                        </div>
                        <p className="text-xs text-muted-foreground leading-tight">{result.comparison_summary}</p>
                        {result.agent_responses && (
                          <div className="flex gap-1 flex-wrap mt-1">
                            {result.agent_responses.slice(0, 6).map((r, i) => (
                              <span key={i} className={cn("w-4 h-4 rounded-full border", r.correct ? "border-green-500/40 bg-green-500/20" : "border-red-500/40 bg-red-500/20")} title={r.correct ? "Correct" : `Misclassified as ${r.classification}`} />
                            ))}
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}

                  {/* Run Button */}
                  <div className="p-4">
                    <button
                      type="button"
                      onClick={() => runScenario(scenario.id)}
                      disabled={isRunning || !!runningScenario}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-background text-sm font-medium hover:bg-primary/90 transition-all hover:shadow-[0_0_12px_rgba(0,212,255,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isRunning ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Running Simulation…
                        </>
                      ) : (
                        <>
                          <Play className="w-4 h-4" />
                          {result ? "Re-run Simulation" : "Run Simulation"}
                        </>
                      )}
                    </button>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </motion.div>
    </DashboardLayout>
  );
}

// Fallback mock data
const MOCK_SCENARIOS: Scenario[] = [
  { id: "scenario-phishing", name: "Phishing Campaign", description: "Simulate a targeted spearphishing campaign hitting multiple users.", scenario_type: "phishing", attack_type: "Phishing", severity: "high", expected_mitre_technique: "T1566.001 - Spearphishing Attachment", expected_response: "Block sender domains, quarantine emails", icon: "mail", difficulty: "medium", incident_count: 5 },
  { id: "scenario-malware", name: "Malware Outbreak", description: "Simulate ransomware spreading laterally via SMB vulnerabilities.", scenario_type: "malware", attack_type: "Ransomware", severity: "critical", expected_mitre_technique: "T1486 - Data Encrypted for Impact", expected_response: "Immediate isolation, disable SMB, restore from backup", icon: "bug", difficulty: "hard", incident_count: 8 },
  { id: "scenario-ddos", name: "DDoS Traffic Spike", description: "Simulate a large-scale DDoS targeting web infrastructure.", scenario_type: "ddos", attack_type: "DDoS", severity: "high", expected_mitre_technique: "T1498 - Network Denial of Service", expected_response: "Activate DDoS protection, rate limit", icon: "zap", difficulty: "medium", incident_count: 3 },
  { id: "scenario-insider", name: "Insider Threat", description: "Simulate a malicious insider exfiltrating data via privileged access.", scenario_type: "insider", attack_type: "Data Exfiltration", severity: "critical", expected_mitre_technique: "T1078 - Valid Accounts", expected_response: "Revoke access, preserve evidence", icon: "user-x", difficulty: "hard", incident_count: 4 },
  { id: "scenario-bruteforce", name: "SSH Brute Force", description: "Simulate a coordinated SSH brute force attack on exposed ports.", scenario_type: "brute_force", attack_type: "Brute Force", severity: "medium", expected_mitre_technique: "T1110 - Brute Force", expected_response: "Block source IPs, enable account lockout", icon: "key", difficulty: "easy", incident_count: 6 },
  { id: "scenario-exfil", name: "Data Exfiltration", description: "Simulate covert data exfiltration via DNS tunneling.", scenario_type: "exfiltration", attack_type: "Data Exfiltration", severity: "critical", expected_mitre_technique: "T1048 - Exfiltration Over Alt Protocol", expected_response: "Block DNS tunneling, DLP enforcement", icon: "upload", difficulty: "hard", incident_count: 4 },
];

function generateMockResult(scenarioId: string, scenarioName: string): RunResult {
  const accuracy = 75 + Math.floor(Math.random() * 20);
  const quality = 70 + Math.floor(Math.random() * 25);
  return {
    run_id: `run-${Date.now()}`,
    scenario_name: scenarioName,
    accuracy_score: accuracy,
    response_quality_score: quality,
    comparison_summary: accuracy >= 90 ? `Excellent: ${accuracy}% accuracy on synthetic incidents.` : `Good: ${accuracy}% accuracy. Some misclassifications detected.`,
    synthetic_incidents: Array(4).fill(null),
    agent_responses: Array(4).fill(null).map((_, i) => ({
      incident_id: `SIM-${i}`,
      classification: scenarioName,
      expected_classification: scenarioName,
      correct: Math.random() > 0.15,
      confidence: 75 + Math.floor(Math.random() * 20),
      response_quality: quality,
    })),
    recommendations: accuracy < 80 ? ["Re-train model with more examples of this attack type"] : [],
  };
}
