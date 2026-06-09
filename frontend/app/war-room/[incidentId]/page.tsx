"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Shield,
  AlertTriangle,
  Clock,
  Activity,
  CheckCircle2,
  XCircle,
  Loader2,
  Brain,
  Search,
  FileText,
  Star,
  Layers,
  Target,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Download,
  Send,
  RefreshCw,
  Wifi,
  WifiOff,
  User,
  ThumbsUp,
  ThumbsDown,
  Edit3,
  ArrowUp,
  RotateCcw,
  Map,
  BarChart2,
  BookOpen,
  Zap,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { SeverityBadge } from "@/components/incidents/SeverityBadge";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import api from "@/lib/api";

// ─── Types ──────────────────────────────────────────────────────────────────

type AgentStepStatus = "pending" | "running" | "completed" | "failed";

interface WarRoomStep {
  id: string;
  name: string;
  status: AgentStepStatus;
  message: string;
  timestamp?: string;
  icon: React.ElementType;
}

interface SimilarIncident {
  id: string;
  severity: string;
  attack_type: string;
  similarity_score: number;
  description: string;
  date: string;
}

interface ThreatIntel {
  ip: string;
  country: string;
  city: string;
  isp: string;
  reputation_score: number;
  is_malicious: boolean;
  abuse_confidence: number;
  threat_categories: string[];
  last_reported: string;
}

interface MitreMapping {
  tactic: string;
  technique: string;
  technique_id: string;
  confidence: number;
  reasoning: string;
}

interface RiskFactor {
  factor: string;
  impact: number;
  reason: string;
}

interface JudgeScores {
  correctness: number;
  safety: number;
  completeness: number;
  actionability: number;
  evidence_alignment: number;
  overall_score: number;
}

interface PlaybookSection {
  title: string;
  steps: string[];
}

interface IncidentData {
  id: string;
  title: string;
  severity: "critical" | "high" | "medium" | "low";
  attack_type: string;
  source_ip: string;
  destination_ip: string;
  timestamp: string;
  status: "analyzing" | "waiting_approval" | "resolved";
  risk_score: number;
  sla_minutes_remaining: number;
  incident_text: string;
  parsed_fields: Record<string, string>;
}

interface AnalysisResult {
  similar_incidents: SimilarIncident[];
  threat_intel: ThreatIntel;
  mitre: MitreMapping;
  risk_score: number;
  risk_factors: RiskFactor[];
  mitigation_recommendation: string;
  mitigation_steps: string[];
  judge_scores: JudgeScores;
  playbook: PlaybookSection[];
  report: string;
}

interface ApprovalState {
  status: "pending" | "approved" | "rejected" | "escalated";
  approved_by?: string;
  timestamp?: string;
  reason?: string;
}

// ─── Mock Data ───────────────────────────────────────────────────────────────

function buildMockIncident(incidentId: string): IncidentData {
  return {
    id: incidentId,
    title: "Ransomware Campaign Targeting Finance Department",
    severity: "critical",
    attack_type: "Ransomware",
    source_ip: "45.33.32.156",
    destination_ip: "192.168.10.45",
    timestamp: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
    status: "waiting_approval",
    risk_score: 87,
    sla_minutes_remaining: 23,
    incident_text:
      "Ransomware detected on finance department workstations. 3 systems showing encrypted files with .locked extension. Source appears to be a phishing email with malicious attachment. Affected IPs: 192.168.10.45, 192.168.10.46, 192.168.10.47. Suspicious process svchost.exe running from %TEMP% folder.",
    parsed_fields: {
      affected_systems: "192.168.10.45, 192.168.10.46, 192.168.10.47",
      file_extension: ".locked",
      suspicious_process: "svchost.exe (TEMP)",
      initial_vector: "Phishing email",
      department: "Finance",
    },
  };
}

const MOCK_RESULT: AnalysisResult = {
  similar_incidents: [
    {
      id: "INC-2024-0821",
      severity: "critical",
      attack_type: "Ransomware",
      similarity_score: 0.94,
      description: "LockBit ransomware on accounting servers",
      date: "2024-03-15",
    },
    {
      id: "INC-2024-0756",
      severity: "high",
      attack_type: "Ransomware",
      similarity_score: 0.87,
      description: "BlackCat ransomware variant on HR workstations",
      date: "2024-02-28",
    },
    {
      id: "INC-2024-0612",
      severity: "critical",
      attack_type: "Ransomware",
      similarity_score: 0.81,
      description: "Ryuk ransomware campaign across finance network",
      date: "2024-01-10",
    },
  ],
  threat_intel: {
    ip: "45.33.32.156",
    country: "Russia",
    city: "Moscow",
    isp: "Linode LLC (proxy)",
    reputation_score: 8,
    is_malicious: true,
    abuse_confidence: 92,
    threat_categories: ["Ransomware", "C2 Server", "Spam Source"],
    last_reported: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
  },
  mitre: {
    tactic: "Impact",
    technique: "Data Encrypted for Impact",
    technique_id: "T1486",
    confidence: 94,
    reasoning:
      "The observed behaviour — file encryption with custom extension, ransom note creation, and process injection via svchost — aligns strongly with T1486. Secondary TTPs include T1566.001 (Spearphishing Attachment) for initial access and T1055 (Process Injection) for persistence.",
  },
  risk_score: 87,
  risk_factors: [
    { factor: "Critical asset exposure", impact: 25, reason: "Finance servers contain PII and financial records" },
    { factor: "Active encryption in progress", impact: 22, reason: "3 systems actively encrypting files" },
    { factor: "Known malicious IP", impact: 20, reason: "Source IP confirmed C2 with 92% abuse confidence" },
    { factor: "Lateral movement possible", impact: 15, reason: "Finance network segment not fully isolated" },
    { factor: "No current backup verified", impact: 5, reason: "Last successful backup 18 hours ago" },
  ],
  mitigation_recommendation:
    "Immediately isolate affected systems 192.168.10.45-47 from the network. Terminate the suspicious svchost.exe process. Block source IP 45.33.32.156 at the perimeter firewall. Initiate incident response playbook for ransomware. Do NOT pay ransom. Contact legal and executive team immediately.",
  mitigation_steps: [
    "Immediately isolate systems 192.168.10.45, .46, .47 from all network segments",
    "Terminate process: svchost.exe running from %TEMP% directory on all affected hosts",
    "Block IP 45.33.32.156 at perimeter firewall and all WAF rules",
    "Preserve memory dumps and volatile evidence before any remediation",
    "Restore from last known-good backup (18h ago) after clean environment is confirmed",
    "Scan all remaining finance network segment hosts with updated AV signatures",
    "Reset credentials for all users in finance department",
    "Notify legal counsel and executive team per breach notification policy",
    "Engage ransomware specialist for decryption analysis",
    "Conduct full post-incident forensic analysis within 72 hours",
  ],
  judge_scores: {
    correctness: 91,
    safety: 96,
    completeness: 88,
    actionability: 93,
    evidence_alignment: 90,
    overall_score: 91,
  },
  playbook: [
    {
      title: "Containment",
      steps: [
        "Isolate affected hosts by disabling NIC or moving to quarantine VLAN",
        "Block source IP at perimeter and internal firewalls",
        "Disable compromised user accounts pending investigation",
        "Preserve all logs: Windows Event, Sysmon, EDR, firewall",
      ],
    },
    {
      title: "Eradication",
      steps: [
        "Terminate malicious process from memory",
        "Remove dropper files and registry persistence keys",
        "Run full AV/EDR scan with latest signatures",
        "Verify no other hosts in segment are infected",
      ],
    },
    {
      title: "Recovery",
      steps: [
        "Restore files from verified clean backup",
        "Rebuild compromised systems from golden image",
        "Validate data integrity post-restore",
        "Bring systems back online with enhanced monitoring",
      ],
    },
    {
      title: "Prevention",
      steps: [
        "Patch all unpatched systems in finance segment",
        "Deploy application whitelisting on workstations",
        "Enable macro execution controls in Office suite",
        "Segment finance network with stricter firewall rules",
      ],
    },
    {
      title: "Communication",
      steps: [
        "Brief CISO and executive team within 2 hours",
        "Notify affected employees and HR department",
        "Evaluate regulatory notification requirements (GDPR/HIPAA)",
        "Prepare external comms if customer data affected",
      ],
    },
    {
      title: "Escalation",
      steps: [
        "Escalate to P1 — engage on-call SOC manager immediately",
        "Notify CISO within 30 minutes per policy",
        "Consider law enforcement engagement for attribution",
        "Engage cyber insurance carrier for coverage review",
      ],
    },
  ],
  report: `# Incident Report: Ransomware Campaign — Finance Department
**Incident ID:** INC-2024-CRITICAL-001
**Severity:** CRITICAL
**Date/Time:** ${new Date(Date.now() - 25 * 60 * 1000).toLocaleString()}
**Status:** Waiting Human Approval

---

## Executive Summary

A critical ransomware infection has been detected across three Finance Department workstations (192.168.10.45–47). The attack vector was a spearphishing email containing a malicious attachment that dropped a ransomware payload disguised as svchost.exe. Files are actively being encrypted with the .locked extension. The source IP (45.33.32.156) has a 92% abuse confidence score and is a known command-and-control server.

## Impact Assessment

- **Affected Systems:** 3 Finance workstations
- **Data at Risk:** Financial records, PII, payroll data
- **Estimated Exposure Window:** ~25 minutes
- **Risk Score:** 87/100 (CRITICAL)

## MITRE ATT&CK Mapping

| Component | Value |
|-----------|-------|
| Tactic | Impact |
| Technique | Data Encrypted for Impact (T1486) |
| Confidence | 94% |

## Recommended Actions

1. Immediately isolate all affected hosts
2. Block source IP at all network boundaries
3. Preserve forensic evidence before remediation
4. Restore from backup after environment verification
5. Engage legal counsel for breach notification assessment

## Risk Factors

| Factor | Impact Score |
|--------|-------------|
| Critical asset exposure | +25 |
| Active encryption | +22 |
| Known malicious IP | +20 |
| Lateral movement risk | +15 |
| Backup gap | +5 |

## Conclusion

This incident represents an active, high-impact ransomware campaign requiring immediate response. Do not pay ransom. All containment steps should be executed within the next 15 minutes to prevent further encryption spread.

---
*Generated by CyberSentinel AI War Room*`,
};

const INITIAL_STEPS: WarRoomStep[] = [
  { id: "validating_input", name: "Validating Input", status: "pending", message: "Extracting incident indicators", icon: Shield },
  { id: "classifying_threat", name: "Classifying Threat", status: "pending", message: "Identifying attack type and severity", icon: AlertTriangle },
  { id: "searching_similar", name: "Searching Similar Incidents", status: "pending", message: "Graph RAG similarity search", icon: Search },
  { id: "querying_graph_rag", name: "Querying Graph RAG", status: "pending", message: "Knowledge graph traversal", icon: Brain },
  { id: "mapping_mitre", name: "Mapping MITRE ATT&CK", status: "pending", message: "Technique and tactic identification", icon: Map },
  { id: "enriching_intel", name: "Enriching Threat Intel", status: "pending", message: "IP reputation & geo lookup", icon: Target },
  { id: "calculating_risk", name: "Calculating Risk Score", status: "pending", message: "Multi-factor risk assessment", icon: BarChart2 },
  { id: "generating_mitigation", name: "Generating Mitigation", status: "pending", message: "Creating response playbook", icon: Layers },
  { id: "running_llm_judge", name: "Running LLM Judge", status: "pending", message: "Evaluating response quality", icon: Star },
  { id: "waiting_approval", name: "Waiting for Human Approval", status: "pending", message: "Human-in-the-loop checkpoint", icon: User },
  { id: "generating_report", name: "Generating Report", status: "pending", message: "Compiling incident report", icon: FileText },
  { id: "completed", name: "Completed", status: "pending", message: "Analysis pipeline complete", icon: CheckCircle2 },
];

// ─── Sub-components ──────────────────────────────────────────────────────────

function StepIcon({ status, Icon }: { status: AgentStepStatus; Icon: React.ElementType }) {
  if (status === "running") return <Loader2 className="w-4 h-4 text-primary animate-spin" />;
  if (status === "completed") return <CheckCircle2 className="w-4 h-4 text-green-400" />;
  if (status === "failed") return <XCircle className="w-4 h-4 text-red-400" />;
  return <Icon className="w-4 h-4 text-muted-foreground" />;
}

function RiskMeter({ score }: { score: number }) {
  const color = score >= 80 ? "#ef4444" : score >= 60 ? "#f97316" : score >= 40 ? "#f59e0b" : "#10b981";
  const circumference = 2 * Math.PI * 45;
  const dashOffset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-28 h-28">
        <svg className="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45" fill="none" stroke="#1f2937" strokeWidth="8" />
          <motion.circle
            cx="50" cy="50" r="45" fill="none"
            stroke={color} strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: dashOffset }}
            transition={{ duration: 1.2, ease: "easeOut" }}
            style={{ filter: `drop-shadow(0 0 6px ${color}60)` }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-black" style={{ color }}>{score}</span>
          <span className="text-xs text-muted-foreground">/100</span>
        </div>
      </div>
      <span className="text-xs font-semibold uppercase tracking-wider" style={{ color }}>
        {score >= 80 ? "Critical" : score >= 60 ? "High" : score >= 40 ? "Medium" : "Low"} Risk
      </span>
    </div>
  );
}

function SlaTimer({ minutesRemaining }: { minutesRemaining: number }) {
  const [mins, setMins] = useState(minutesRemaining);
  const isUrgent = mins / minutesRemaining < 0.2;

  useEffect(() => {
    const t = setInterval(() => setMins((m) => Math.max(0, m - 1)), 60000);
    return () => clearInterval(t);
  }, []);

  const pct = Math.max(0, (mins / minutesRemaining) * 100);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground flex items-center gap-1">
          <Clock className="w-3.5 h-3.5" /> SLA Countdown
        </span>
        <span className={cn("font-mono font-bold", isUrgent ? "text-red-400 animate-pulse" : "text-foreground")}>
          {mins}m remaining
        </span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <motion.div
          className={cn("h-full rounded-full", isUrgent ? "bg-red-500" : "bg-primary")}
          initial={{ width: "100%" }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5 }}
          style={isUrgent ? { boxShadow: "0 0 8px rgba(239,68,68,0.6)" } : {}}
        />
      </div>
    </div>
  );
}

function AccordionCard({ title, icon: Icon, children, defaultOpen = false }: {
  title: string; icon: React.ElementType; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-muted/30 transition-colors"
        onClick={() => setOpen(!open)}
      >
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium text-foreground">{title}</span>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-t border-border"
          >
            <div className="px-4 py-3">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const color = value >= 80 ? "bg-green-500" : value >= 60 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground capitalize">{label.replace(/_/g, " ")}</span>
        <span className="font-mono font-semibold text-foreground">{value}%</span>
      </div>
      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
        <motion.div
          className={cn("h-full rounded-full", color)}
          initial={{ width: "0%" }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

const TABS = [
  { id: "overview", label: "Overview", icon: Activity },
  { id: "investigation", label: "Live Investigation", icon: Brain },
  { id: "evidence", label: "Evidence & Intel", icon: Search },
  { id: "mitre", label: "MITRE ATT&CK", icon: Map },
  { id: "risk", label: "Risk & Mitigation", icon: BarChart2 },
  { id: "approval", label: "Approval & Playbook", icon: BookOpen },
  { id: "report", label: "Report", icon: FileText },
];

export default function WarRoomPage() {
  const params = useParams();
  const router = useRouter();
  const incidentId = params?.incidentId as string;

  const [activeTab, setActiveTab] = useState("overview");
  const [incident, setIncident] = useState<IncidentData | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [steps, setSteps] = useState<WarRoomStep[]>(INITIAL_STEPS);
  const [wsStatus, setWsStatus] = useState<"connecting" | "connected" | "disconnected">("disconnected");
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<{ role: "user" | "assistant"; content: string }[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [approval, setApproval] = useState<ApprovalState>({ status: "pending" });
  const [editedMitigation, setEditedMitigation] = useState("");
  const [copiedStep, setCopiedStep] = useState<number | null>(null);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const analysisStarted = useRef(false);

  // ── Load incident data ──
  useEffect(() => {
    const fetchIncident = async () => {
      try {
        const res = await api.get(`/war-room/${incidentId}`);
        setIncident(res.data);
      } catch {
        setIncident(buildMockIncident(incidentId));
      }
    };
    if (incidentId) fetchIncident();
  }, [incidentId]);

  // ── WebSocket connection ──
  useEffect(() => {
    if (!incidentId || analysisStarted.current) return;
    analysisStarted.current = true;

    const wsBase = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
    const wsUrl = `${wsBase}/api/v1/ws/war-room/${incidentId}`;

    const runMockTimeline = () => {
      const stepIds = INITIAL_STEPS.map((s) => s.id);
      let idx = 0;
      const advance = () => {
        if (idx >= stepIds.length) {
          setResult(MOCK_RESULT);
          setEditedMitigation(MOCK_RESULT.mitigation_recommendation);
          return;
        }
        const currentId = stepIds[idx];
        setSteps((prev) =>
          prev.map((s) =>
            s.id === currentId ? { ...s, status: "running", timestamp: new Date().toLocaleTimeString() } : s
          )
        );
        setTimeout(() => {
          setSteps((prev) =>
            prev.map((s) =>
              s.id === currentId ? { ...s, status: "completed" } : s
            )
          );
          idx++;
          setTimeout(advance, 600 + Math.random() * 800);
        }, 1200 + Math.random() * 1000);
      };
      setTimeout(advance, 800);
    };

    setWsStatus("connecting");
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsStatus("connected");
        if (incident) {
          ws.send(JSON.stringify({ action: "analyze", incident_text: incident.incident_text }));
        }
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "step_update") {
            setSteps((prev) =>
              prev.map((s) =>
                s.id === msg.step_id
                  ? { ...s, status: msg.status, message: msg.message || s.message, timestamp: new Date().toLocaleTimeString() }
                  : s
              )
            );
          } else if (msg.type === "result") {
            setResult(msg.data || MOCK_RESULT);
            setEditedMitigation(msg.data?.mitigation_recommendation || MOCK_RESULT.mitigation_recommendation);
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onerror = () => {
        setWsStatus("disconnected");
        runMockTimeline();
      };

      ws.onclose = () => setWsStatus("disconnected");
    } catch {
      setWsStatus("disconnected");
      runMockTimeline();
    }

    return () => {
      wsRef.current?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [incidentId]);

  // ── Scroll chat to bottom ──
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // ── Chat send ──
  const sendChat = useCallback(async () => {
    if (!chatInput.trim() || chatLoading) return;
    const userMsg = chatInput.trim();
    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setChatLoading(true);
    try {
      const res = await api.post("/war-room/chat", { incident_id: incidentId, message: userMsg });
      setChatMessages((prev) => [...prev, { role: "assistant", content: res.data.response }]);
    } catch {
      const mockResponses: Record<string, string> = {
        default: "Based on the current analysis, I recommend prioritising network isolation of the affected hosts before attempting any remediation. The ransomware strain appears to be LockBit 3.0 based on the .locked extension pattern.",
      };
      setChatMessages((prev) => [...prev, { role: "assistant", content: mockResponses.default }]);
    }
    setChatLoading(false);
  }, [chatInput, chatLoading, incidentId]);

  // ── Approval actions ──
  const handleApprove = (action: "approve" | "reject" | "edit_approve" | "regenerate" | "escalate") => {
    const actionMap: Record<string, ApprovalState> = {
      approve: { status: "approved", approved_by: "Analyst — SOC Team", timestamp: new Date().toISOString(), reason: "Reviewed and approved" },
      reject: { status: "rejected", approved_by: "Analyst — SOC Team", timestamp: new Date().toISOString(), reason: "Rejected — insufficient containment steps" },
      edit_approve: { status: "approved", approved_by: "Analyst — SOC Team", timestamp: new Date().toISOString(), reason: "Approved with edits" },
      escalate: { status: "escalated", approved_by: "Analyst — SOC Team", timestamp: new Date().toISOString(), reason: "Escalated to CISO" },
    };
    if (action === "regenerate") {
      toast.info("Regenerating mitigation recommendation...");
      setTimeout(() => {
        setEditedMitigation(MOCK_RESULT.mitigation_recommendation + " [Regenerated]");
        toast.success("Mitigation regenerated");
      }, 2000);
      return;
    }
    setApproval(actionMap[action]);
    toast.success(`Action: ${action.replace("_", " ")} completed`);
  };

  // ── Copy step ──
  const copyStep = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedStep(idx);
    setTimeout(() => setCopiedStep(null), 2000);
  };

  // ── Export playbook ──
  const exportPlaybook = () => {
    if (!result) return;
    const md = result.playbook
      .map((section) => `## ${section.title}\n\n${section.steps.map((s, i) => `${i + 1}. ${s}`).join("\n")}`)
      .join("\n\n---\n\n");
    const blob = new Blob([`# Incident Response Playbook\n\n${md}`], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `playbook-${incidentId}.md`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Playbook exported");
  };

  // ── Download report ──
  const downloadReport = () => {
    if (!result) return;
    const blob = new Blob([result.report], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report-${incidentId}.md`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Report downloaded");
  };

  const generateReport = () => {
    setIsGeneratingReport(true);
    setTimeout(() => setIsGeneratingReport(false), 2000);
    toast.success("Report generated");
  };

  // ── Loading state ──
  if (!incident) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center gap-3 text-muted-foreground">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
            <span>Loading incident war room...</span>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  const completedSteps = steps.filter((s) => s.status === "completed").length;
  const pipelineProgress = (completedSteps / steps.length) * 100;

  return (
    <DashboardLayout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="max-w-full"
      >
        {/* ── Page Header ── */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              <span className="text-xs font-mono text-muted-foreground uppercase tracking-widest">AI Incident War Room</span>
              <span className="text-xs font-mono text-primary border border-primary/30 bg-primary/10 px-2 py-0.5 rounded">{incidentId}</span>
            </div>
            <h1 className="text-xl font-bold text-foreground">{incident.title}</h1>
            <div className="flex items-center gap-3 mt-2">
              <SeverityBadge severity={incident.severity} />
              <span className="text-xs text-muted-foreground border border-border rounded px-2 py-0.5">{incident.attack_type}</span>
              <span
                className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", {
                  "border-primary/40 bg-primary/10 text-primary": incident.status === "analyzing",
                  "border-amber-500/40 bg-amber-500/10 text-amber-400": incident.status === "waiting_approval",
                  "border-green-500/40 bg-green-500/10 text-green-400": incident.status === "resolved",
                })}
              >
                {incident.status.replace("_", " ")}
              </span>
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                {wsStatus === "connected" ? (
                  <><Wifi className="w-3 h-3 text-green-400" /><span className="text-green-400">Live</span></>
                ) : (
                  <><WifiOff className="w-3 h-3" />{wsStatus}</>
                )}
              </span>
            </div>
          </div>
          <button
            onClick={() => router.push("/incidents")}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border hover:bg-muted text-muted-foreground hover:text-foreground text-sm transition-colors"
          >
            <RotateCcw className="w-4 h-4" /> New Incident
          </button>
        </div>

        {/* ── Pipeline Progress Bar ── */}
        <div className="mb-6">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5">
            <span>Analysis Pipeline</span>
            <span className="font-mono">{completedSteps}/{steps.length} steps</span>
          </div>
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-primary via-purple-500 to-green-500 rounded-full"
              animate={{ width: `${pipelineProgress}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>

        {/* ── Tabs ── */}
        <div className="flex gap-1 mb-6 overflow-x-auto pb-1 scrollbar-hide">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all",
                  activeTab === tab.id
                    ? "bg-primary text-background shadow-[0_0_15px_rgba(0,212,255,0.3)]"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* ── Tab Content ── */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >

            {/* ── Overview Tab ── */}
            {activeTab === "overview" && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Incident Summary Card */}
                <div className="lg:col-span-2 cyber-card p-6 border border-border">
                  <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
                    <Shield className="w-4 h-4 text-primary" /> Incident Summary
                  </h2>
                  <div className="grid grid-cols-2 gap-4">
                    {[
                      { label: "Attack Type", value: incident.attack_type },
                      { label: "Source IP", value: incident.source_ip },
                      { label: "Destination IP", value: incident.destination_ip },
                      { label: "Timestamp", value: new Date(incident.timestamp).toLocaleString() },
                    ].map((item) => (
                      <div key={item.label}>
                        <p className="text-xs text-muted-foreground mb-1">{item.label}</p>
                        <p className="text-sm font-mono text-foreground">{item.value}</p>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 pt-4 border-t border-border">
                    <p className="text-xs text-muted-foreground mb-2">Incident Text</p>
                    <p className="text-sm text-foreground leading-relaxed bg-muted rounded-lg p-3">
                      {incident.incident_text}
                    </p>
                  </div>
                </div>

                {/* Right column */}
                <div className="space-y-4">
                  {/* Risk Meter */}
                  <div className="cyber-card p-5 border border-border flex flex-col items-center gap-3">
                    <h3 className="text-sm font-semibold text-foreground self-start">Risk Score</h3>
                    <RiskMeter score={incident.risk_score} />
                  </div>

                  {/* SLA Timer */}
                  <div className="cyber-card p-5 border border-border">
                    <SlaTimer minutesRemaining={incident.sla_minutes_remaining} />
                  </div>

                  {/* Status */}
                  <div className="cyber-card p-5 border border-border">
                    <h3 className="text-xs text-muted-foreground mb-2">Analysis Status</h3>
                    <div className="flex items-center gap-2">
                      <div className={cn("w-2 h-2 rounded-full", {
                        "bg-primary animate-pulse": incident.status === "analyzing",
                        "bg-amber-400": incident.status === "waiting_approval",
                        "bg-green-400": incident.status === "resolved",
                      })} />
                      <span className="text-sm font-medium text-foreground capitalize">
                        {incident.status.replace("_", " ")}
                      </span>
                    </div>
                    <div className="mt-3 text-xs text-muted-foreground">
                      Pipeline: {completedSteps}/{steps.length} steps complete
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ── Live Investigation Tab ── */}
            {activeTab === "investigation" && (
              <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                {/* Agent Timeline (60%) */}
                <div className="lg:col-span-3 cyber-card p-5 border border-border">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                      <Brain className="w-4 h-4 text-primary" /> Agent Pipeline
                    </h2>
                    <span className="text-xs text-muted-foreground font-mono">
                      {completedSteps}/{steps.length}
                    </span>
                  </div>
                  <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
                    {steps.map((step, i) => {
                      const Icon = step.icon;
                      return (
                        <motion.div
                          key={step.id}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.03 }}
                          className={cn(
                            "relative flex items-start gap-3 p-3 rounded-lg border transition-all",
                            step.status === "running" && "border-primary/50 bg-primary/5 shadow-[0_0_12px_rgba(0,212,255,0.1)]",
                            step.status === "completed" && "border-green-500/30 bg-green-500/5",
                            step.status === "failed" && "border-red-500/30 bg-red-500/5",
                            step.status === "pending" && "border-border bg-card/50 opacity-60"
                          )}
                        >
                          {step.status === "running" && (
                            <div className="absolute inset-0 rounded-lg bg-primary/3 animate-pulse pointer-events-none" />
                          )}
                          {/* Icon */}
                          <div className={cn("w-8 h-8 rounded-lg border flex items-center justify-center shrink-0", {
                            "border-primary/40 bg-primary/10": step.status === "running",
                            "border-green-500/40 bg-green-500/10": step.status === "completed",
                            "border-red-500/40 bg-red-500/10": step.status === "failed",
                            "border-border bg-muted": step.status === "pending",
                          })}>
                            <StepIcon status={step.status} Icon={Icon} />
                          </div>
                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className={cn("text-sm font-medium", step.status === "pending" ? "text-muted-foreground" : "text-foreground")}>
                                {step.name}
                              </span>
                              {step.status === "running" && (
                                <span className="text-xs text-primary font-mono animate-pulse">RUNNING</span>
                              )}
                              {step.status === "completed" && (
                                <span className="text-xs text-green-400 font-mono">DONE</span>
                              )}
                            </div>
                            <p className="text-xs text-muted-foreground mt-0.5">{step.message}</p>
                          </div>
                          {/* Timestamp */}
                          {step.timestamp && (
                            <span className="text-xs text-muted-foreground font-mono shrink-0">{step.timestamp}</span>
                          )}
                          {/* Running progress bar */}
                          {step.status === "running" && (
                            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-muted overflow-hidden rounded-b-lg">
                              <motion.div
                                className="h-full bg-primary"
                                animate={{ x: ["-100%", "100%"] }}
                                transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                              />
                            </div>
                          )}
                        </motion.div>
                      );
                    })}
                  </div>
                </div>

                {/* Analyst Chat (40%) */}
                <div className="lg:col-span-2 cyber-card p-5 border border-border flex flex-col">
                  <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-primary" /> Analyst Chat
                  </h2>
                  <div className="flex-1 space-y-3 overflow-y-auto min-h-[400px] max-h-[500px] pr-1 mb-4">
                    {chatMessages.length === 0 && (
                      <div className="flex flex-col items-center justify-center h-32 text-center">
                        <Brain className="w-8 h-8 text-muted-foreground/30 mb-2" />
                        <p className="text-xs text-muted-foreground">Ask the AI analyst anything about this incident</p>
                      </div>
                    )}
                    {chatMessages.map((msg, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={cn("flex gap-2", msg.role === "user" ? "justify-end" : "justify-start")}
                      >
                        {msg.role === "assistant" && (
                          <div className="w-6 h-6 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center shrink-0 mt-0.5">
                            <Brain className="w-3 h-3 text-primary" />
                          </div>
                        )}
                        <div className={cn("max-w-[85%] rounded-lg px-3 py-2 text-xs leading-relaxed", {
                          "bg-primary text-background": msg.role === "user",
                          "bg-muted border border-border text-foreground": msg.role === "assistant",
                        })}>
                          {msg.content}
                        </div>
                      </motion.div>
                    ))}
                    {chatLoading && (
                      <div className="flex gap-2 items-center">
                        <div className="w-6 h-6 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center shrink-0">
                          <Brain className="w-3 h-3 text-primary" />
                        </div>
                        <div className="bg-muted border border-border rounded-lg px-3 py-2">
                          <div className="flex gap-1 items-center">
                            <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                            <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                            <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                          </div>
                        </div>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>
                  <div className="flex gap-2">
                    <textarea
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); } }}
                      placeholder="Ask about this incident..."
                      rows={2}
                      className="flex-1 cyber-input resize-none text-xs"
                    />
                    <button
                      onClick={sendChat}
                      disabled={!chatInput.trim() || chatLoading}
                      className="px-3 py-2 bg-primary text-background rounded-lg hover:bg-primary/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-[0_0_12px_rgba(0,212,255,0.3)] self-end"
                    >
                      <Send className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* ── Evidence & Intel Tab ── */}
            {activeTab === "evidence" && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Similar Incidents */}
                <div className="cyber-card border border-border overflow-hidden">
                  <div className="px-5 py-4 border-b border-border">
                    <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                      <Search className="w-4 h-4 text-primary" /> Similar Incidents
                    </h2>
                  </div>
                  <div className="divide-y divide-border">
                    {(result?.similar_incidents || MOCK_RESULT.similar_incidents).map((inc) => (
                      <div key={inc.id} className="flex items-center gap-3 px-5 py-3 hover:bg-muted/30 transition-colors">
                        <SeverityBadge severity={inc.severity as "critical" | "high" | "medium" | "low"} size="sm" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-foreground truncate">{inc.description}</p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-xs text-purple-400">{inc.attack_type}</span>
                            <span className="text-xs text-muted-foreground">{inc.date}</span>
                          </div>
                        </div>
                        <div className="text-right shrink-0">
                          <div className="text-sm font-bold text-primary">{Math.round(inc.similarity_score * 100)}%</div>
                          <div className="text-xs text-muted-foreground">match</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Threat Intel */}
                <div className="space-y-4">
                  <div className="cyber-card p-5 border border-red-500/20 bg-red-500/5">
                    <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
                      <Target className="w-4 h-4 text-red-400" /> IP Reputation: {(result?.threat_intel || MOCK_RESULT.threat_intel).ip}
                    </h2>
                    {(() => {
                      const intel = result?.threat_intel || MOCK_RESULT.threat_intel;
                      return (
                        <div className="space-y-3">
                          <div className="grid grid-cols-2 gap-3">
                            {[
                              { label: "Country", value: intel.country },
                              { label: "City", value: intel.city },
                              { label: "ISP", value: intel.isp },
                              { label: "Last Reported", value: new Date(intel.last_reported).toLocaleDateString() },
                            ].map((item) => (
                              <div key={item.label}>
                                <p className="text-xs text-muted-foreground">{item.label}</p>
                                <p className="text-sm font-mono text-foreground">{item.value}</p>
                              </div>
                            ))}
                          </div>
                          <div className="flex items-center justify-between pt-3 border-t border-border">
                            <div>
                              <p className="text-xs text-muted-foreground mb-1">Reputation Score</p>
                              <div className="flex items-center gap-2">
                                <div className="h-2 w-24 bg-muted rounded-full overflow-hidden">
                                  <div className="h-full bg-red-500 rounded-full" style={{ width: `${intel.reputation_score * 10}%` }} />
                                </div>
                                <span className="text-sm font-bold text-red-400">{intel.reputation_score}/10</span>
                              </div>
                            </div>
                            <div>
                              <p className="text-xs text-muted-foreground mb-1">Abuse Confidence</p>
                              <span className="text-lg font-black text-red-400">{intel.abuse_confidence}%</span>
                            </div>
                            <div>
                              <span className={cn("px-2.5 py-1 rounded-full text-xs font-semibold border", intel.is_malicious ? "bg-red-500/15 border-red-500/40 text-red-400" : "bg-green-500/15 border-green-500/40 text-green-400")}>
                                {intel.is_malicious ? "MALICIOUS" : "CLEAN"}
                              </span>
                            </div>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground mb-1.5">Threat Categories</p>
                            <div className="flex flex-wrap gap-1.5">
                              {intel.threat_categories.map((cat) => (
                                <span key={cat} className="px-2 py-0.5 text-xs rounded border border-red-500/30 bg-red-500/10 text-red-400">{cat}</span>
                              ))}
                            </div>
                          </div>
                        </div>
                      );
                    })()}
                  </div>

                  {/* Evidence Summary */}
                  <div className="cyber-card p-5 border border-border">
                    <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                      <FileText className="w-4 h-4 text-primary" /> Parsed Evidence Fields
                    </h2>
                    <div className="space-y-2">
                      {Object.entries(incident.parsed_fields).map(([k, v]) => (
                        <div key={k} className="flex items-start gap-2 text-xs">
                          <span className="text-muted-foreground capitalize shrink-0 w-36">{k.replace(/_/g, " ")}:</span>
                          <span className="font-mono text-foreground">{v}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ── MITRE ATT&CK Tab ── */}
            {activeTab === "mitre" && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* MITRE Mapping Card */}
                <div className="cyber-card p-6 border border-purple-500/20 bg-purple-500/5">
                  {(() => {
                    const mitre = result?.mitre || MOCK_RESULT.mitre;
                    return (
                      <>
                        <h2 className="text-sm font-semibold text-foreground mb-5 flex items-center gap-2">
                          <Map className="w-4 h-4 text-purple-400" /> MITRE ATT&amp;CK Mapping
                        </h2>
                        <div className="space-y-4">
                          <div className="flex flex-wrap gap-3">
                            <div>
                              <p className="text-xs text-muted-foreground mb-1.5">Tactic</p>
                              <span className="px-3 py-1.5 rounded-lg text-sm font-semibold border border-purple-500/40 bg-purple-500/15 text-purple-400">
                                {mitre.tactic}
                              </span>
                            </div>
                            <div>
                              <p className="text-xs text-muted-foreground mb-1.5">Technique</p>
                              <span className="px-3 py-1.5 rounded-lg text-sm font-semibold border border-red-500/40 bg-red-500/15 text-red-400">
                                {mitre.technique}
                              </span>
                            </div>
                            <div>
                              <p className="text-xs text-muted-foreground mb-1.5">Technique ID</p>
                              <span className="px-3 py-1.5 rounded-lg text-sm font-mono font-bold border border-primary/40 bg-primary/10 text-primary">
                                {mitre.technique_id}
                              </span>
                            </div>
                          </div>

                          <div>
                            <div className="flex items-center justify-between mb-1.5">
                              <p className="text-xs text-muted-foreground">Confidence</p>
                              <span className="text-sm font-bold text-primary">{mitre.confidence}%</span>
                            </div>
                            <div className="h-2 bg-muted rounded-full overflow-hidden">
                              <motion.div
                                className="h-full bg-gradient-to-r from-primary to-purple-500 rounded-full"
                                initial={{ width: "0%" }}
                                animate={{ width: `${mitre.confidence}%` }}
                                transition={{ duration: 0.8, ease: "easeOut" }}
                              />
                            </div>
                          </div>

                          <div className="pt-3 border-t border-border">
                            <p className="text-xs text-muted-foreground mb-2">ATT&amp;CK Reasoning</p>
                            <p className="text-sm text-foreground leading-relaxed">{mitre.reasoning}</p>
                          </div>
                        </div>
                      </>
                    );
                  })()}
                </div>

                {/* Mitigation Recommendations */}
                <div className="cyber-card p-6 border border-border">
                  <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
                    <Layers className="w-4 h-4 text-primary" /> Mitigation Recommendations
                  </h2>
                  <div className="space-y-2">
                    {(result?.mitigation_steps || MOCK_RESULT.mitigation_steps).slice(0, 6).map((step, i) => (
                      <div key={i} className="flex items-start gap-2.5 text-sm group">
                        <span className="text-primary font-mono font-bold shrink-0 mt-0.5">{String(i + 1).padStart(2, "0")}.</span>
                        <span className="text-foreground leading-relaxed flex-1">{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* ── Risk & Mitigation Tab ── */}
            {activeTab === "risk" && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Risk Score + Factors */}
                <div className="space-y-4">
                  {/* Score bar */}
                  <div className="cyber-card p-5 border border-border">
                    <h2 className="text-sm font-semibold text-foreground mb-4">Risk Score Breakdown</h2>
                    <div className="flex items-center gap-4 mb-4">
                      <RiskMeter score={result?.risk_score || MOCK_RESULT.risk_score} />
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Total Risk Score</p>
                        <p className="text-4xl font-black text-red-400">{result?.risk_score || MOCK_RESULT.risk_score}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">out of 100</p>
                      </div>
                    </div>
                    <div className="h-4 bg-muted rounded-full overflow-hidden">
                      <motion.div
                        className="h-full rounded-full"
                        style={{ background: "linear-gradient(to right, #10b981, #f59e0b, #ef4444)" }}
                        initial={{ width: "0%" }}
                        animate={{ width: `${result?.risk_score || MOCK_RESULT.risk_score}%` }}
                        transition={{ duration: 1, ease: "easeOut" }}
                      />
                    </div>
                  </div>

                  {/* Risk factors */}
                  <div className="cyber-card p-5 border border-border">
                    <h3 className="text-sm font-semibold text-foreground mb-3">Risk Factors</h3>
                    <div className="space-y-2">
                      {(result?.risk_factors || MOCK_RESULT.risk_factors).map((factor, i) => (
                        <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-muted/50 border border-border">
                          <span className={cn("shrink-0 px-2 py-0.5 rounded text-xs font-mono font-bold border", {
                            "bg-red-500/15 border-red-500/40 text-red-400": factor.impact >= 20,
                            "bg-orange-500/15 border-orange-500/40 text-orange-400": factor.impact >= 15 && factor.impact < 20,
                            "bg-amber-500/15 border-amber-500/40 text-amber-400": factor.impact < 15,
                          })}>
                            +{factor.impact}
                          </span>
                          <div>
                            <p className="text-sm font-medium text-foreground">{factor.factor}</p>
                            <p className="text-xs text-muted-foreground mt-0.5">{factor.reason}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Mitigation steps + Judge scores */}
                <div className="space-y-4">
                  {/* Mitigation steps */}
                  <div className="cyber-card p-5 border border-border">
                    <h3 className="text-sm font-semibold text-foreground mb-3">Mitigation Steps</h3>
                    <div className="space-y-2">
                      {(result?.mitigation_steps || MOCK_RESULT.mitigation_steps).map((step, i) => (
                        <div key={i} className="flex items-start gap-2 group">
                          <span className="text-primary font-mono text-xs font-bold shrink-0 mt-1">{String(i + 1).padStart(2, "0")}.</span>
                          <p className="text-sm text-foreground leading-relaxed flex-1">{step}</p>
                          <button
                            onClick={() => copyStep(step, i)}
                            className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:text-primary"
                          >
                            {copiedStep === i ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5 text-muted-foreground" />}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Judge scorecard */}
                  <div className="cyber-card p-5 border border-border">
                    <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
                      <Star className="w-4 h-4 text-amber-400" /> LLM Judge Scorecard
                    </h3>
                    <div className="space-y-3">
                      {Object.entries(result?.judge_scores || MOCK_RESULT.judge_scores).map(([metric, score]) => (
                        <ScoreBar key={metric} label={metric} value={score as number} />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ── Approval & Playbook Tab ── */}
            {activeTab === "approval" && (
              <div className="space-y-6">
                {/* Approval Panel */}
                <div className="cyber-card p-6 border border-border">
                  <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
                    <User className="w-4 h-4 text-primary" /> Human-in-the-Loop Approval
                  </h2>

                  {approval.status !== "pending" ? (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={cn("p-4 rounded-lg border", {
                        "border-green-500/40 bg-green-500/10": approval.status === "approved",
                        "border-red-500/40 bg-red-500/10": approval.status === "rejected",
                        "border-purple-500/40 bg-purple-500/10": approval.status === "escalated",
                      })}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <CheckCircle2 className={cn("w-5 h-5", {
                          "text-green-400": approval.status === "approved",
                          "text-red-400": approval.status === "rejected",
                          "text-purple-400": approval.status === "escalated",
                        })} />
                        <span className="font-semibold text-foreground capitalize">{approval.status}</span>
                      </div>
                      <div className="grid grid-cols-3 gap-3 text-xs">
                        <div><p className="text-muted-foreground">By</p><p className="font-medium text-foreground">{approval.approved_by}</p></div>
                        <div><p className="text-muted-foreground">Time</p><p className="font-medium text-foreground">{approval.timestamp ? new Date(approval.timestamp).toLocaleTimeString() : "—"}</p></div>
                        <div><p className="text-muted-foreground">Reason</p><p className="font-medium text-foreground">{approval.reason}</p></div>
                      </div>
                    </motion.div>
                  ) : (
                    <div className="space-y-4">
                      <div>
                        <p className="text-xs text-muted-foreground mb-2">Current Mitigation Recommendation</p>
                        <textarea
                          value={editedMitigation}
                          onChange={(e) => setEditedMitigation(e.target.value)}
                          rows={5}
                          className="w-full cyber-input resize-none text-sm"
                        />
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => handleApprove("approve")}
                          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-green-500/15 border border-green-500/40 text-green-400 hover:bg-green-500/25 transition-colors text-sm font-medium"
                        >
                          <ThumbsUp className="w-4 h-4" /> Approve
                        </button>
                        <button
                          onClick={() => handleApprove("reject")}
                          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-red-500/15 border border-red-500/40 text-red-400 hover:bg-red-500/25 transition-colors text-sm font-medium"
                        >
                          <ThumbsDown className="w-4 h-4" /> Reject
                        </button>
                        <button
                          onClick={() => handleApprove("edit_approve")}
                          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary/15 border border-primary/40 text-primary hover:bg-primary/25 transition-colors text-sm font-medium"
                        >
                          <Edit3 className="w-4 h-4" /> Edit &amp; Approve
                        </button>
                        <button
                          onClick={() => handleApprove("regenerate")}
                          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-500/15 border border-amber-500/40 text-amber-400 hover:bg-amber-500/25 transition-colors text-sm font-medium"
                        >
                          <RefreshCw className="w-4 h-4" /> Regenerate
                        </button>
                        <button
                          onClick={() => handleApprove("escalate")}
                          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-purple-500/15 border border-purple-500/40 text-purple-400 hover:bg-purple-500/25 transition-colors text-sm font-medium"
                        >
                          <ArrowUp className="w-4 h-4" /> Escalate
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Playbook */}
                <div className="cyber-card border border-border overflow-hidden">
                  <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                    <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                      <BookOpen className="w-4 h-4 text-primary" /> Incident Response Playbook
                    </h2>
                    <button
                      onClick={exportPlaybook}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border hover:border-primary/40 hover:text-primary text-muted-foreground text-xs transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" /> Export Playbook
                    </button>
                  </div>
                  <div className="p-4 space-y-2">
                    {(result?.playbook || MOCK_RESULT.playbook).map((section, i) => (
                      <AccordionCard
                        key={section.title}
                        title={section.title}
                        icon={[Shield, Target, RefreshCw, Layers, Activity, ArrowUp][i] || Shield}
                        defaultOpen={i === 0}
                      >
                        <ol className="space-y-2 mt-1">
                          {section.steps.map((step, j) => (
                            <li key={j} className="flex items-start gap-2 text-sm">
                              <span className="text-primary font-mono font-bold shrink-0 mt-0.5">{j + 1}.</span>
                              <span className="text-foreground leading-relaxed">{step}</span>
                            </li>
                          ))}
                        </ol>
                      </AccordionCard>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* ── Report Tab ── */}
            {activeTab === "report" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <FileText className="w-4 h-4 text-primary" /> Incident Report
                  </h2>
                  <div className="flex gap-2">
                    <button
                      onClick={generateReport}
                      disabled={isGeneratingReport}
                      className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border hover:border-primary/40 hover:text-primary text-muted-foreground text-xs transition-colors disabled:opacity-50"
                    >
                      {isGeneratingReport ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                      Generate Markdown
                    </button>
                    <button
                      onClick={downloadReport}
                      className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-primary text-background text-xs font-medium hover:bg-primary/90 transition-all hover:shadow-[0_0_12px_rgba(0,212,255,0.3)]"
                    >
                      <Download className="w-3.5 h-3.5" /> Download PDF
                    </button>
                  </div>
                </div>
                <div className="cyber-card p-6 border border-border">
                  <pre className="text-sm text-foreground leading-relaxed whitespace-pre-wrap font-mono overflow-auto max-h-[600px]">
                    {result?.report || MOCK_RESULT.report}
                  </pre>
                </div>
              </div>
            )}

          </motion.div>
        </AnimatePresence>
      </motion.div>
    </DashboardLayout>
  );
}
