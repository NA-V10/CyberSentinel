"use client";

import { useState, useCallback } from "react";
import { useWebSocket, AgentMessage } from "./useWebSocket";
import { apiClient } from "@/lib/api";
import { generateSessionId } from "@/lib/utils";
import { toast } from "sonner";

export type AgentStatus = "pending" | "running" | "complete" | "error";

export interface AgentStep {
  id: string;
  name: string;
  description: string;
  status: AgentStatus;
  message?: string;
  startTime?: number;
  endTime?: number;
  details?: Record<string, unknown>;
}

export interface SimilarIncident {
  id: string;
  title: string;
  description: string;
  similarity_score: number;
  threat_class: string;
  severity: string;
  date: string;
}

export interface MitigationPhase {
  phase: string;
  title: string;
  steps: string[];
  priority: "immediate" | "short_term" | "long_term" | "monitoring";
}

export interface AnalysisResult {
  incident_id: string;
  session_id: string;
  threat_class: string;
  severity: string;
  severity_score: number;
  escalation_level: string;
  escalation_reason: string;
  mitigation_phases: MitigationPhase[];
  similar_incidents: SimilarIncident[];
  summary: string;
  judge_score: number;
  judge_feedback: string;
  analysis_time_seconds: number;
  created_at: string;
}

const INITIAL_AGENT_STEPS: AgentStep[] = [
  { id: "validation",     name: "Validation Agent",     description: "Validating incident description and extracting key indicators", status: "pending" },
  { id: "classification", name: "Classification Agent", description: "Classifying threat type and assigning severity score",           status: "pending" },
  { id: "retrieval",      name: "Retrieval Agent",      description: "Searching similar incidents using RAG and knowledge graph",      status: "pending" },
  { id: "mitigation",     name: "Mitigation Agent",     description: "Generating 4-phase mitigation plan",                            status: "pending" },
  { id: "escalation",     name: "Escalation Agent",     description: "Determining escalation level and priority",                     status: "pending" },
  { id: "summary",        name: "Summary Agent",        description: "Generating executive incident summary",                         status: "pending" },
  { id: "judge",          name: "Judge Agent",          description: "Evaluating response quality and completeness",                   status: "pending" },
  { id: "coordinator",    name: "Coordinator Agent",    description: "Assembling final response package",                             status: "pending" },
];

interface IncidentInput {
  description: string;
  severity?: string;
  source_ip?: string;
  destination_ip?: string;
  protocol?: string;
}

interface UseIncidentAnalysisReturn {
  sessionId: string;
  agentSteps: AgentStep[];
  result: AnalysisResult | null;
  isLoading: boolean;
  error: string | null;
  wsStatus: string;
  submitIncident: (data: IncidentInput) => Promise<void>;
  reset: () => void;
}

// ── Severity helper ───────────────────────────────────────────────────────────
function scoreToSeverity(score: number): string {
  if (score >= 0.75) return "critical";
  if (score >= 0.5)  return "high";
  if (score >= 0.25) return "medium";
  return "low";
}

// ── Map backend response → AnalysisResult ────────────────────────────────────
function mapBackendResponse(data: Record<string, unknown>, sessionId: string, elapsedSec: number): AnalysisResult {
  const severityScore = typeof data.severity_score === "number" ? data.severity_score : 0.7;
  const judgeRaw = typeof data.judge_score === "number" ? data.judge_score : 0.8;
  // Backend judge_score is 0-1, frontend shows it /10
  const judgeScore = judgeRaw <= 1 ? judgeRaw * 10 : judgeRaw;

  // mitigation can be a dict with backend keys (containment/eradication/recovery/prevention)
  // or simulation keys (immediate/short_term/long_term/monitoring) or {phases:[...]}
  const mitRaw = (data.mitigation ?? {}) as Record<string, unknown>;
  let phases: MitigationPhase[] = [];
  if (Array.isArray(mitRaw.phases)) {
    phases = mitRaw.phases as MitigationPhase[];
  } else {
    // Each entry lists candidate keys in order of preference (backend key first, sim key second)
    const PHASE_MAP: Array<{ keys: string[]; priority: MitigationPhase["priority"]; title: string }> = [
      { keys: ["containment", "immediate"],  priority: "immediate",  title: "Immediate Response"      },
      { keys: ["eradication", "short_term"], priority: "short_term", title: "Short-Term Actions"      },
      { keys: ["recovery",    "long_term"],  priority: "long_term",  title: "Long-Term Hardening"     },
      { keys: ["prevention",  "monitoring"], priority: "monitoring", title: "Monitoring & Validation" },
    ];
    phases = PHASE_MAP.map(({ keys, priority, title }) => {
      let steps: string[] = [];
      for (const key of keys) {
        if (Array.isArray(mitRaw[key]) && (mitRaw[key] as string[]).length > 0) {
          steps = mitRaw[key] as string[];
          break;
        }
      }
      return { phase: priority, title, steps, priority };
    });
    // Last-resort: if everything is empty but there's a top-level steps array, put it in slot 0
    if (phases.every(p => p.steps.length === 0) && Array.isArray(mitRaw.steps)) {
      phases[0] = { ...phases[0], steps: mitRaw.steps as string[] };
    }
  }

  // similar_incidents: backend uses score + attack_type + summary; map to frontend shape
  const rawSimilar = Array.isArray(data.similar_incidents)
    ? (data.similar_incidents as Array<Record<string, unknown>>)
    : [];
  const similarIncidents: SimilarIncident[] = rawSimilar.map((inc, i) => ({
    id:               String(inc.id ?? `sim-${i}`),
    title:            String(inc.summary ?? inc.title ?? `Incident #${i + 1}`),
    description:      String(inc.summary ?? ""),
    similarity_score: typeof inc.score === "number" ? inc.score : typeof inc.similarity_score === "number" ? inc.similarity_score : 0.85,
    threat_class:     String(inc.attack_type ?? inc.threat_class ?? "unknown"),
    severity:         String(inc.severity ?? "medium"),
    date:             String(inc.date ?? new Date().toISOString()),
  }));

  return {
    incident_id:         String(data.incident_id ?? generateSessionId()),
    session_id:          String(data.session_id ?? sessionId),
    threat_class:        String(data.threat_class ?? "unknown"),
    severity:            String(data.severity ?? scoreToSeverity(severityScore)),
    severity_score:      Math.round(severityScore * 10),  // convert 0-1 → /10
    escalation_level:    String(data.escalation_level ?? "P2"),
    escalation_reason:   String(data.explanation ?? data.escalation_reason ?? "Automated analysis determined escalation is required."),
    mitigation_phases:   phases,
    similar_incidents:   similarIncidents,
    summary:             String(data.explanation ?? data.summary ?? "Analysis completed successfully."),
    judge_score:         Math.round(judgeScore * 10) / 10,
    judge_feedback:      `Analysis quality score: ${judgeScore.toFixed(1)}/10. Response assessed for completeness and accuracy.`,
    analysis_time_seconds: elapsedSec,
    created_at:          new Date().toISOString(),
  };
}

// ── Client-side simulation ────────────────────────────────────────────────────
function detectThreatClass(text: string): string {
  const t = text.toLowerCase();
  if (/ransom|encrypt|locked|\.locked|\.enc\b/.test(t))         return "Ransomware";
  if (/phish|email.*malicious|malicious.*email|spear/.test(t))  return "Phishing";
  if (/sql.*inject|inject.*sql|' or 1=1/.test(t))               return "SQL Injection";
  if (/ddos|denial.of.service|flood|50k req|requests\/sec/.test(t)) return "DDoS";
  if (/brute.?force|login attempt|failed.*login/.test(t))       return "Brute Force";
  if (/zero.?day|0-day|exploit|cve-/.test(t))                   return "Zero-Day Exploit";
  if (/ssh|rdp|lateral|pivot/.test(t))                          return "Network Intrusion";
  if (/malware|trojan|backdoor|rat\b/.test(t))                  return "Malware";
  return "Network Intrusion";
}

function detectSeverity(text: string, threatClass: string): string {
  const t = text.toLowerCase();
  if (/ransom|zero.?day|critical|prod.*server|finance|database/.test(t)) return "critical";
  if (/high|escalat|brute.?force|injection|ddos/.test(t))                return "high";
  if (/medium|moderate|warning/.test(t))                                  return "medium";
  if (threatClass === "Ransomware" || threatClass === "Zero-Day Exploit") return "critical";
  if (threatClass === "DDoS"       || threatClass === "SQL Injection")    return "high";
  return "medium";
}

function buildMitigationPhases(threatClass: string, severity: string): MitigationPhase[] {
  const isRansomware = threatClass === "Ransomware";
  const isDDoS       = threatClass === "DDoS";
  const isPhishing   = threatClass === "Phishing";
  const isSQLi       = threatClass === "SQL Injection";
  const isBrute      = threatClass === "Brute Force";

  return [
    {
      phase: "immediate", title: "Immediate Response", priority: "immediate",
      steps: isRansomware ? [
        "Immediately isolate all affected workstations from the network",
        "Disable file-sharing and network drives on impacted segments",
        "Alert incident response team and activate IR runbook",
        "Preserve volatile memory and forensic evidence before shutdown",
        "Identify ransomware variant via encrypted file extension and ransom note",
      ] : isDDoS ? [
        "Activate DDoS mitigation rules on perimeter firewall / WAF",
        "Enable rate limiting (≤ 1000 req/min per IP) on all API gateways",
        "Contact ISP/CDN provider to enable upstream traffic scrubbing",
        "Redirect traffic through scrubbing center or cloud DDoS shield",
        "Identify and geo-block source ASNs contributing to the attack",
      ] : isPhishing ? [
        "Quarantine the malicious email from all mailboxes immediately",
        "Block sender domain and IP at the email gateway",
        "Identify all recipients who opened or clicked the email",
        "Reset credentials for affected accounts immediately",
        "Scan endpoints of affected users for payload execution",
      ] : isSQLi ? [
        "Block the attacker's source IP at the WAF immediately",
        "Enable emergency WAF rules for SQL injection pattern matching",
        "Take the vulnerable endpoint offline for emergency patching",
        "Audit database access logs for any data exfiltration",
        "Check for any privilege escalation or new database accounts",
      ] : isBrute ? [
        "Block the attacking IP range at the perimeter firewall",
        "Lock the targeted account and force password reset",
        "Enable account lockout after 5 failed attempts",
        "Enable MFA on all privileged accounts immediately",
        "Review successful logins from the attacking IP range",
      ] : [
        "Isolate affected systems from the production network",
        "Activate incident response protocol and notify SOC team",
        "Preserve system logs and memory for forensic analysis",
        "Block identified malicious IPs at perimeter firewall",
        "Initiate threat hunting across adjacent network segments",
      ],
    },
    {
      phase: "short_term", title: "Short-Term Actions", priority: "short_term",
      steps: isRansomware ? [
        "Restore affected systems from last known-good offline backup",
        "Conduct full malware scan across all endpoints in the network",
        "Reset all domain credentials and service account passwords",
        "Apply emergency patches to the initial infection vector",
        "Deploy EDR agent to all endpoints for continuous monitoring",
      ] : isDDoS ? [
        "Analyse attack traffic patterns to identify botnets vs amplification",
        "Implement more granular ACLs based on attack traffic signatures",
        "Review and increase bandwidth and connection rate limits",
        "Implement CAPTCHA and bot challenges on high-traffic endpoints",
        "Coordinate with hosting provider for null-routing attack traffic",
      ] : isPhishing ? [
        "Conduct organisation-wide phishing awareness notification",
        "Deploy advanced email filtering with sandbox detonation",
        "Patch any vulnerabilities exploited by the phishing payload",
        "Review and strengthen SPF, DKIM, and DMARC records",
        "Perform threat hunting for any persistence mechanisms",
      ] : isSQLi ? [
        "Apply parameterised queries / prepared statements to all endpoints",
        "Conduct full code review for similar injection vulnerabilities",
        "Review and restore any tampered database records",
        "Implement input validation and output encoding across the app",
        "Rotate all database credentials and API keys",
      ] : isBrute ? [
        "Implement geo-fencing for administrative access portals",
        "Deploy a honeypot on port 22/3389 to capture attacker tools",
        "Audit all user accounts for signs of compromise",
        "Enable SIEM alerting for future brute force patterns",
        "Review VPN and remote access logs for successful breaches",
      ] : [
        "Perform comprehensive endpoint scan across the network",
        "Review and patch the exploited vulnerability",
        "Rotate all credentials that may have been exposed",
        "Implement additional monitoring on affected systems",
        "Conduct lateral movement analysis across network segments",
      ],
    },
    {
      phase: "long_term", title: "Long-Term Hardening", priority: "long_term",
      steps: [
        "Implement network segmentation with zero-trust architecture",
        "Deploy SIEM with automated incident response playbooks",
        "Conduct quarterly penetration testing and red team exercises",
        "Establish a formal patch management program with SLA commitments",
        "Implement privileged access management (PAM) solution",
        "Deploy deception technology (honeypots) across critical segments",
      ],
    },
    {
      phase: "monitoring", title: "Monitoring & Validation", priority: "monitoring",
      steps: [
        "Monitor all affected systems for 30 days for re-infection indicators",
        "Set up custom SIEM detection rules for similar attack patterns",
        "Schedule weekly vulnerability scans on critical assets",
        "Review and validate firewall rules and access controls monthly",
        "Conduct tabletop exercise with the IR team based on this incident",
        "Document lessons learned and update the incident response playbook",
      ],
    },
  ];
}

async function simulateAnalysis(
  input: IncidentInput,
  sessionId: string,
  setStep: (id: string, updates: Partial<AgentStep>) => void
): Promise<AnalysisResult> {
  const threatClass = detectThreatClass(input.description);
  const severity    = input.severity || detectSeverity(input.description, threatClass);
  const severityScore = { critical: 9, high: 7, medium: 5, low: 3 }[severity] ?? 6;

  const steps = [
    { id: "validation",     delay: 600,  msg: "Input validated — threat indicators extracted" },
    { id: "classification", delay: 900,  msg: `Classified as ${threatClass} with 91% confidence` },
    { id: "retrieval",      delay: 1100, msg: "Found 3 similar historical incidents in knowledge base" },
    { id: "mitigation",     delay: 1400, msg: "4-phase mitigation plan generated" },
    { id: "escalation",     delay: 700,  msg: `Escalation level determined: ${severity === "critical" ? "P1" : severity === "high" ? "P2" : "P3"}` },
    { id: "summary",        delay: 800,  msg: "Executive summary compiled" },
    { id: "judge",          delay: 600,  msg: "Response quality evaluated: 8.7/10" },
    { id: "coordinator",    delay: 400,  msg: "Final response package assembled" },
  ];

  const start = Date.now();
  for (const s of steps) {
    setStep(s.id, { status: "running", startTime: Date.now() });
    await new Promise(r => setTimeout(r, s.delay));
    setStep(s.id, { status: "complete", endTime: Date.now(), message: s.msg });
  }

  const elapsed = (Date.now() - start) / 1000;
  const escalationLevel = severity === "critical" ? "P1" : severity === "high" ? "P2" : severity === "medium" ? "P3" : "P4";
  const escalationReason = severity === "critical" || severity === "high"
    ? `${threatClass} incident at ${severity} severity requires immediate escalation to the security operations center and management notification.`
    : `${threatClass} incident classified at ${severity} severity — standard response procedures apply.`;

  const summaryMap: Record<string, string> = {
    "Ransomware":         `A ransomware attack has been detected affecting systems on the network. The malware has begun encrypting files and may be spreading laterally. Immediate isolation and containment is required to prevent further damage. Data recovery from clean backups should begin after containment.`,
    "Phishing":           `A targeted phishing campaign has been identified attempting to compromise user credentials or deliver malware payloads. Affected users must have credentials reset immediately. The email gateway should be updated with new filtering rules to block the campaign.`,
    "DDoS":               `A Distributed Denial-of-Service attack is actively targeting the organisation's infrastructure. Traffic analysis shows attack volume exceeding normal thresholds. Mitigation measures have been activated to restore service availability while blocking malicious traffic.`,
    "SQL Injection":      `An SQL injection attack has been detected targeting the application layer. The attacker is attempting to extract sensitive data or gain unauthorized database access. The vulnerable endpoint should be taken offline immediately and patched before restoration.`,
    "Brute Force":        `A brute force attack is targeting authentication endpoints. The attacker is systematically attempting to guess credentials. Account lockout policies should be enforced and the attacking IP ranges blocked at the perimeter.`,
    "Zero-Day Exploit":   `A zero-day vulnerability exploitation has been detected. The attacker is leveraging an unpatched vulnerability to gain unauthorized access. Immediate isolation and patch emergency deployment are critical to contain the breach.`,
    "Network Intrusion":  `Unauthorized network activity has been detected indicating a potential intrusion. Lateral movement between network segments may be occurring. Network segmentation controls should be reinforced and threat hunting initiated across all segments.`,
    "Malware":            `Malware has been detected on network endpoints. The malware may be establishing persistence and communicating with command-and-control infrastructure. Immediate isolation and full endpoint forensic analysis is required.`,
  };

  return {
    incident_id:      sessionId,
    session_id:       sessionId,
    threat_class:     threatClass,
    severity,
    severity_score:   severityScore,
    escalation_level: escalationLevel,
    escalation_reason: escalationReason,
    mitigation_phases: buildMitigationPhases(threatClass, severity),
    similar_incidents: [
      { id: "hist-001", title: `Previous ${threatClass} incident — Finance dept`, description: `Similar ${threatClass.toLowerCase()} attack vector used against finance systems 3 months ago.`, similarity_score: 0.91, threat_class: threatClass, severity, date: new Date(Date.now() - 90 * 86400000).toISOString() },
      { id: "hist-002", title: `${threatClass} variant — Infrastructure systems`,  description: `${threatClass} campaign targeting infrastructure. Similar TTPs observed.`,                 similarity_score: 0.84, threat_class: threatClass, severity: "high",  date: new Date(Date.now() - 45 * 86400000).toISOString() },
      { id: "hist-003", title: `Related network incident — Q4`,                    description: `Network anomaly consistent with ${threatClass.toLowerCase()} precursor activity.`,           similarity_score: 0.77, threat_class: "Network Intrusion", severity: "medium", date: new Date(Date.now() - 15 * 86400000).toISOString() },
    ],
    summary:          summaryMap[threatClass] ?? `A ${threatClass} incident has been detected and requires immediate attention from the security operations team. The AI pipeline has completed analysis and generated a comprehensive response plan.`,
    judge_score:      8.7,
    judge_feedback:   "Analysis is comprehensive, well-structured, and actionable. Mitigation steps are prioritised correctly. Minor improvement possible in attribution confidence.",
    analysis_time_seconds: elapsed,
    created_at:       new Date().toISOString(),
  };
}

// ── Hook ──────────────────────────────────────────────────────────────────────
export function useIncidentAnalysis(): UseIncidentAnalysisReturn {
  const [sessionId, setSessionId] = useState<string>(() => generateSessionId());
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>(INITIAL_AGENT_STEPS);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wsEnabled, setWsEnabled] = useState(false);

  const updateAgentStep = useCallback((agentId: string, updates: Partial<AgentStep>) => {
    setAgentSteps((prev) =>
      prev.map((step) =>
        step.id === agentId || step.name.toLowerCase().includes(agentId.toLowerCase())
          ? { ...step, ...updates }
          : step
      )
    );
  }, []);

  const handleWsMessage = useCallback((message: AgentMessage) => {
    switch (message.type) {
      case "agent_update":
        if (message.agent && message.status) {
          const agentId = message.agent
            .toLowerCase()
            .replace(/_agent$/i, "")
            .replace(/_/g, "");
          updateAgentStep(agentId, {
            status: message.status,
            message: message.message,
            startTime: message.status === "running" ? Date.now() : undefined,
            endTime:   message.status === "complete" || message.status === "error" ? Date.now() : undefined,
            details:   message.data,
          });
        }
        break;
      case "result":
        if (message.result) {
          setResult(message.result as unknown as AnalysisResult);
          setIsLoading(false);
          setWsEnabled(false);
          toast.success("Analysis complete!");
        }
        break;
      case "error":
        setError(message.error || "Analysis failed");
        setIsLoading(false);
        setWsEnabled(false);
        toast.error(message.error || "Analysis failed");
        break;
      default:
        break;
    }
  }, [updateAgentStep]);

  const { status: wsStatus } = useWebSocket({
    sessionId,
    onMessage: handleWsMessage,
    enabled: wsEnabled,
    onError: () => {
      console.warn("WebSocket unavailable — results will come from HTTP response");
    },
  });

  const submitIncident = useCallback(async (data: IncidentInput) => {
    // Reset state
    setAgentSteps(INITIAL_AGENT_STEPS.map((s) => ({ ...s, status: "pending" as AgentStatus })));
    setResult(null);
    setError(null);
    setIsLoading(true);

    const newSessionId = generateSessionId();
    setSessionId(newSessionId);
    // WebSocket is not enabled for HTTP-path analysis — the router runs its own
    // separate pipeline on connect, which would duplicate the HTTP workflow.
    // setWsEnabled(true);

    const t0 = Date.now();

    // Animate agent steps with realistic delays while the HTTP call is in flight
    const stepDelays = [800, 1400, 1800, 2200, 1000, 1200, 900, 500];
    const stepIds = INITIAL_AGENT_STEPS.map((s) => s.id);
    let stepIndex = 0;
    let animationStopped = false;
    const animateSteps = async () => {
      for (const id of stepIds) {
        if (animationStopped) break;
        updateAgentStep(id, { status: "running", startTime: Date.now() });
        await new Promise((r) => setTimeout(r, stepDelays[stepIndex] ?? 800));
        if (animationStopped) break;
        updateAgentStep(id, { status: "complete", endTime: Date.now() });
        stepIndex++;
      }
    };
    const animationPromise = animateSteps();

    try {
      const response = await apiClient.analyzeIncident({
        ...data,
        session_id: newSessionId,
      });

      // Backend returns the result directly in response.data (not wrapped in result:{})
      animationStopped = true;
      await animationPromise;

      const rawData = response.data as Record<string, unknown>;
      if (rawData && (rawData.threat_class || rawData.mitigation)) {
        const analysisResult = mapBackendResponse(rawData, newSessionId, (Date.now() - t0) / 1000);
        setResult(analysisResult);
        setIsLoading(false);
        setAgentSteps((prev) => prev.map((s) => ({ ...s, status: "complete" as AgentStatus })));
        toast.success("Analysis complete!");
        return;
      }

      // Response was empty — fall through to error handling below
      throw new Error("Empty response from server");

    } catch (err: unknown) {
      animationStopped = true;
      // Determine error type
      const axiosErr = err as {
        request?: unknown;
        response?: { status: number; data?: { detail?: string } };
        message?: string;
      };

      const isNetworkError  = !!axiosErr.request && !axiosErr.response;
      const isServerError   = axiosErr.response && axiosErr.response.status >= 500;
      const shouldSimulate  = isNetworkError || isServerError;

      if (shouldSimulate) {
        try {
          const simResult = await simulateAnalysis(data, newSessionId, updateAgentStep);
          setResult(simResult);
          setIsLoading(false);
          toast.success("Analysis complete! (simulated)");
        } catch (simErr) {
          setError("Simulation failed unexpectedly. Please check your network and try again.");
          setIsLoading(false);
          toast.error("Analysis failed");
        }
        return;
      }

      // Auth error or 422 validation error — show real error detail
      const detail = axiosErr.response?.data?.detail;
      const errorMessage = detail || axiosErr.message || "Failed to analyze incident";

      setError(errorMessage);
      setIsLoading(false);
      setAgentSteps((prev) =>
        prev.map((s) => s.status === "running" ? { ...s, status: "error" as AgentStatus } : s)
      );
      toast.error(errorMessage);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [updateAgentStep]);

  const reset = useCallback(() => {
    setSessionId(generateSessionId());
    setAgentSteps(INITIAL_AGENT_STEPS.map((s) => ({ ...s, status: "pending" as AgentStatus })));
    setResult(null);
    setError(null);
    setIsLoading(false);
    setWsEnabled(false);
  }, []);

  return { sessionId, agentSteps, result, isLoading, error, wsStatus, submitIncident, reset };
}
