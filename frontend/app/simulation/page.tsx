"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Play,
  Zap,
  Shield,
  Mail,
  Terminal,
  Cloud,
  Database,
  ArrowUpRight,
  Info,
  Loader2,
  CheckCircle2,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import api from "@/lib/api";

// ─── Types ──────────────────────────────────────────────────────────────────

interface Scenario {
  id: string;
  name: string;
  category: string;
  attack_type: string;
  severity: "critical" | "high" | "medium" | "low";
  description: string;
  tags: string[];
  icon: React.ElementType;
  accent: string;
}

// ─── Static Scenarios ────────────────────────────────────────────────────────

const SCENARIOS: Scenario[] = [
  {
    id: "phishing-campaign",
    name: "Phishing Email Campaign",
    category: "Initial Access",
    attack_type: "Phishing",
    severity: "high",
    description:
      "A sophisticated spearphishing campaign targets the HR and Finance departments with malicious Office attachments masquerading as payroll updates. Macro-enabled documents drop credential-harvesting payloads.",
    tags: ["T1566", "Email", "Credential Theft", "Social Engineering"],
    icon: Mail,
    accent: "orange",
  },
  {
    id: "brute-force-ssh",
    name: "Brute Force SSH Attack",
    category: "Credential Access",
    attack_type: "Brute Force",
    severity: "high",
    description:
      "An automated credential-stuffing attack originates from a botnet of compromised IPs targeting the production jump server. Over 12,000 failed attempts in 30 minutes preceding a successful login.",
    tags: ["T1110", "SSH", "Port 22", "Botnet"],
    icon: Terminal,
    accent: "orange",
  },
  {
    id: "malware-infection",
    name: "Malware Infection",
    category: "Execution & Persistence",
    attack_type: "Ransomware",
    severity: "critical",
    description:
      "LockBit 3.0 ransomware spreads laterally across the finance segment after initial execution via a malicious svchost.exe dropped in %TEMP%. Files on 4 servers encrypted within 8 minutes of infection.",
    tags: ["T1486", "LockBit", "Ransomware", "Lateral Movement"],
    icon: Shield,
    accent: "red",
  },
  {
    id: "ddos-spike",
    name: "DDoS Traffic Spike",
    category: "Impact",
    attack_type: "DDoS",
    severity: "critical",
    description:
      "A volumetric UDP flood at 148 Gbps saturates the edge network, causing complete service disruption to the public API and customer portal. Attack originates from 14,000 amplified DNS reflectors.",
    tags: ["T1498", "UDP Flood", "DNS Amplification", "148 Gbps"],
    icon: Cloud,
    accent: "red",
  },
  {
    id: "unauthorized-access",
    name: "Unauthorized Access",
    category: "Defense Evasion",
    attack_type: "Insider Threat",
    severity: "high",
    description:
      "A privileged insider account accesses production database backups during off-hours, bypasses DLP controls, and exfiltrates 2.3 GB of customer PII to an external cloud storage endpoint.",
    tags: ["T1078", "Insider Threat", "Data Theft", "Privilege Abuse"],
    icon: Database,
    accent: "orange",
  },
  {
    id: "data-exfiltration",
    name: "Suspicious Data Exfiltration",
    category: "Exfiltration",
    attack_type: "APT Exfiltration",
    severity: "critical",
    description:
      "An APT group uses DNS tunneling and encrypted C2 channels to exfiltrate 8.7 GB of intellectual property from R&D servers over 72 hours, evading DLP by splitting data into 512-byte chunks.",
    tags: ["T1048", "DNS Tunnel", "APT", "C2 Channel"],
    icon: ArrowUpRight,
    accent: "red",
  },
];

const SEVERITY_STYLES: Record<string, { badge: string; border: string; bg: string; glow: string }> = {
  critical: {
    badge: "bg-red-500/15 border-red-500/40 text-red-400",
    border: "border-red-500/30",
    bg: "bg-red-500/5",
    glow: "shadow-[0_0_20px_rgba(239,68,68,0.15)]",
  },
  high: {
    badge: "bg-orange-500/15 border-orange-500/40 text-orange-400",
    border: "border-orange-500/30",
    bg: "bg-orange-500/5",
    glow: "shadow-[0_0_20px_rgba(249,115,22,0.1)]",
  },
  medium: {
    badge: "bg-amber-500/15 border-amber-500/40 text-amber-400",
    border: "border-amber-500/30",
    bg: "bg-amber-500/5",
    glow: "",
  },
  low: {
    badge: "bg-green-500/15 border-green-500/40 text-green-400",
    border: "border-green-500/30",
    bg: "bg-green-500/5",
    glow: "",
  },
};

const CATEGORY_COLORS: Record<string, string> = {
  "Initial Access": "text-blue-400 border-blue-400/30 bg-blue-400/10",
  "Credential Access": "text-orange-400 border-orange-400/30 bg-orange-400/10",
  "Execution & Persistence": "text-red-400 border-red-400/30 bg-red-400/10",
  Impact: "text-red-400 border-red-400/30 bg-red-400/10",
  "Defense Evasion": "text-purple-400 border-purple-400/30 bg-purple-400/10",
  Exfiltration: "text-cyan-400 border-cyan-400/30 bg-cyan-400/10",
};

// ─── Scenario Card ────────────────────────────────────────────────────────────

function ScenarioCard({
  scenario,
  onRun,
  isRunning,
}: {
  scenario: Scenario;
  onRun: (id: string) => void;
  isRunning: boolean;
}) {
  const styles = SEVERITY_STYLES[scenario.severity];
  const CategoryColor = CATEGORY_COLORS[scenario.category] || "text-muted-foreground border-border bg-muted";
  const Icon = scenario.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2, transition: { duration: 0.15 } }}
      className={cn(
        "cyber-card p-5 border flex flex-col gap-4 transition-all duration-300 group",
        styles.border,
        styles.bg,
        "hover:border-opacity-60",
        styles.glow
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className={cn("w-10 h-10 rounded-lg border flex items-center justify-center shrink-0 transition-all", styles.badge)}>
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-foreground text-sm leading-tight group-hover:text-primary transition-colors">
              {scenario.name}
            </h3>
            <span className={cn("inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border mt-1", CategoryColor)}>
              {scenario.category}
            </span>
          </div>
        </div>
        {/* Severity badge */}
        <span className={cn("shrink-0 px-2.5 py-1 rounded-full text-xs font-semibold border uppercase tracking-wide", styles.badge)}>
          {scenario.severity}
        </span>
      </div>

      {/* Attack type */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Attack Type:</span>
        <span className="text-xs font-medium text-foreground border border-border px-2 py-0.5 rounded bg-muted/50">
          {scenario.attack_type}
        </span>
      </div>

      {/* Description */}
      <p className="text-xs text-muted-foreground leading-relaxed flex-1">{scenario.description}</p>

      {/* Tags */}
      <div className="flex flex-wrap gap-1.5">
        {scenario.tags.map((tag) => (
          <span
            key={tag}
            className="px-2 py-0.5 text-xs rounded border border-border bg-muted/50 text-muted-foreground font-mono"
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Run button */}
      <button
        onClick={() => onRun(scenario.id)}
        disabled={isRunning}
        className={cn(
          "w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all",
          "bg-primary text-background hover:bg-primary/90 hover:shadow-[0_0_20px_rgba(0,212,255,0.4)]",
          "disabled:opacity-60 disabled:cursor-not-allowed"
        )}
      >
        {isRunning ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" /> Launching...
          </>
        ) : (
          <>
            <Play className="w-4 h-4" /> Run Simulation
          </>
        )}
      </button>
    </motion.div>
  );
}

// ─── Launch Modal ─────────────────────────────────────────────────────────────

function LaunchModal({
  scenario,
  progress,
}: {
  scenario: Scenario | null;
  progress: number;
}) {
  if (!scenario) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/90 backdrop-blur-md"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="cyber-card border border-primary/30 p-10 max-w-md w-full mx-4 text-center shadow-[0_0_60px_rgba(0,212,255,0.15)]"
      >
        {/* Pulsing icon */}
        <div className="relative inline-flex mb-6">
          <div className="absolute inset-0 rounded-full bg-primary/20 animate-ping" />
          <div className="relative w-16 h-16 rounded-full bg-primary/10 border border-primary/40 flex items-center justify-center">
            {progress < 100 ? (
              <Zap className="w-8 h-8 text-primary animate-pulse" />
            ) : (
              <CheckCircle2 className="w-8 h-8 text-green-400" />
            )}
          </div>
        </div>

        <h2 className="text-xl font-bold text-foreground mb-1">
          {progress < 100 ? "Launching Simulation..." : "Simulation Ready!"}
        </h2>
        <p className="text-muted-foreground text-sm mb-2">{scenario.name}</p>
        <span className={cn("inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border mb-6 uppercase tracking-wide", SEVERITY_STYLES[scenario.severity].badge)}>
          {scenario.severity}
        </span>

        {/* Progress bar */}
        <div className="space-y-2">
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-primary to-purple-500 rounded-full"
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.1 }}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>
              {progress < 30
                ? "Initialising scenario..."
                : progress < 60
                ? "Injecting incident data..."
                : progress < 90
                ? "Connecting AI pipeline..."
                : "Redirecting to War Room..."}
            </span>
            <span className="font-mono">{Math.round(progress)}%</span>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function SimulationPage() {
  const router = useRouter();
  const [scenarios] = useState<Scenario[]>(SCENARIOS);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [launchScenario, setLaunchScenario] = useState<Scenario | null>(null);
  const [progress, setProgress] = useState(0);

  const runSimulation = async (scenarioId: string) => {
    const scenario = scenarios.find((s) => s.id === scenarioId);
    if (!scenario || runningId) return;

    setRunningId(scenarioId);
    setLaunchScenario(scenario);
    setProgress(0);

    // Try to create a simulation session via API
    let simulationIncidentId = `simulation-${scenarioId}`;
    try {
      const res = await api.post("/simulation/run", { scenario_id: scenarioId });
      simulationIncidentId = res.data?.incident_id || simulationIncidentId;
    } catch {
      // Proceed with mock ID
    }

    // Animate progress bar over 3 seconds
    const startTime = Date.now();
    const duration = 3000;
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const pct = Math.min((elapsed / duration) * 100, 100);
      setProgress(pct);
      if (pct < 100) {
        requestAnimationFrame(animate);
      } else {
        toast.success(`Simulation "${scenario.name}" launched!`);
        setTimeout(() => {
          router.push(`/war-room/${simulationIncidentId}`);
        }, 400);
      }
    };
    requestAnimationFrame(animate);
  };

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
            <div className="flex items-center gap-2 mb-2">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-primary/30 bg-primary/10 text-primary text-xs font-medium">
                <Zap className="w-3 h-3" />
                Demo Mode
              </div>
            </div>
            <h1 className="text-2xl font-bold text-foreground">Simulation Mode</h1>
            <p className="text-muted-foreground text-sm mt-1">
              Demo-ready attack scenario simulator — full AI analysis pipeline
            </p>
          </div>
        </div>

        {/* ── Scenario Grid ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5 mb-8">
          {scenarios.map((scenario, i) => (
            <motion.div
              key={scenario.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: i * 0.07 }}
            >
              <ScenarioCard
                scenario={scenario}
                onRun={runSimulation}
                isRunning={runningId === scenario.id}
              />
            </motion.div>
          ))}
        </div>

        {/* ── Info Box ── */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.5 }}
          className="flex items-start gap-3 px-5 py-4 rounded-lg border border-primary/20 bg-primary/5"
        >
          <Info className="w-5 h-5 text-primary shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-foreground mb-0.5">About Simulation Mode</p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Simulation mode uses realistic incident data for demo purposes. All scenarios run the full AI analysis pipeline — including threat classification, MITRE ATT&amp;CK mapping, risk scoring, mitigation generation, and LLM judge evaluation. Perfect for panel presentations and executive demos.
            </p>
          </div>
        </motion.div>
      </motion.div>

      {/* ── Launch Modal ── */}
      <AnimatePresence>
        {launchScenario && (
          <LaunchModal scenario={launchScenario} progress={progress} />
        )}
      </AnimatePresence>
    </DashboardLayout>
  );
}
