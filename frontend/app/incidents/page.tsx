"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  Play,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Info,
  Wifi,
  WifiOff,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { AgentTimeline } from "@/components/incidents/AgentTimeline";
import {
  SeverityBadge,
  EscalationBadge,
  ThreatClassBadge,
} from "@/components/incidents/SeverityBadge";
import { useIncidentAnalysis } from "@/hooks/useIncidentAnalysis";
import { formatDate } from "@/lib/utils";
import { toast } from "sonner";
import type { MitigationPhase, SimilarIncident } from "@/hooks/useIncidentAnalysis";

const SAMPLE_INCIDENTS = [
  "Ransomware detected on finance department workstations. 3 systems showing encrypted files with .locked extension. Source appears to be a phishing email with malicious attachment. Affected IPs: 192.168.10.45, 192.168.10.46, 192.168.10.47",
  "SSH brute force attack detected. 5000 failed login attempts from IP 45.33.32.156 targeting our jump server on port 22 over last 30 minutes.",
  "SQL injection attempt on customer portal API. Malicious payload detected in query parameter: ' OR 1=1 -- targeting /api/users endpoint from IP 203.0.113.100",
];

interface AccordionItemProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  badge?: string;
  badgeColor?: string;
}

function AccordionItem({
  title,
  children,
  defaultOpen = false,
  badge,
  badgeColor = "bg-muted text-muted-foreground",
}: AccordionItemProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 hover:bg-muted/30 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground">{title}</span>
          {badge && (
            <span
              className={`px-2 py-0.5 rounded-full text-xs font-medium border ${badgeColor}`}
            >
              {badge}
            </span>
          )}
        </div>
        {isOpen ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 border-t border-border">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

const phaseColors: Record<string, string> = {
  immediate: "border-red-500/30 bg-red-500/5",
  short_term: "border-orange-500/30 bg-orange-500/5",
  long_term: "border-blue-500/30 bg-blue-500/5",
  monitoring: "border-green-500/30 bg-green-500/5",
};

const phaseLabels: Record<string, string> = {
  immediate: "Immediate Response",
  short_term: "Short-Term Actions",
  long_term: "Long-Term Hardening",
  monitoring: "Monitoring & Validation",
};

const phaseBadgeColors: Record<string, string> = {
  immediate: "bg-red-500/15 border-red-500/40 text-red-400",
  short_term: "bg-orange-500/15 border-orange-500/40 text-orange-400",
  long_term: "bg-blue-500/15 border-blue-500/40 text-blue-400",
  monitoring: "bg-green-500/15 border-green-500/40 text-green-400",
};

export default function IncidentsPage() {
  const searchParams = useSearchParams();
  const prefilledDescription = searchParams.get("description") || "";

  const [description, setDescription] = useState(prefilledDescription);
  const [severity, setSeverity] = useState("");
  const [sourceIp, setSourceIp] = useState("");
  const [destIp, setDestIp] = useState("");
  const [protocol, setProtocol] = useState("");
  const [showOptional, setShowOptional] = useState(false);
  const [copiedId, setCopiedId] = useState(false);

  const {
    agentSteps,
    result,
    isLoading,
    error,
    wsStatus,
    submitIncident,
    reset,
    sessionId,
  } = useIncidentAnalysis();

  const hasStarted = isLoading || result !== null || error !== null;

  const handleSubmit = async () => {
    if (!description.trim()) {
      toast.error("Please enter an incident description");
      return;
    }

    await submitIncident({
      description: description.trim(),
      severity: severity || undefined,
      source_ip: sourceIp || undefined,
      destination_ip: destIp || undefined,
      protocol: protocol || undefined,
    });
  };

  const handleReset = () => {
    reset();
    setDescription("");
    setSeverity("");
    setSourceIp("");
    setDestIp("");
    setProtocol("");
  };

  const copySessionId = () => {
    navigator.clipboard.writeText(sessionId);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  return (
    <DashboardLayout>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Incident Analysis
            </h1>
            <p className="text-muted-foreground text-sm mt-1">
              Describe an incident to trigger multi-agent AI analysis
            </p>
          </div>
          {hasStarted && (
            <button
              onClick={handleReset}
              className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border hover:bg-muted text-muted-foreground hover:text-foreground text-sm transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              New Analysis
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {/* Left: Input + Agent Timeline */}
          <div className="space-y-6">
            {/* Input Panel */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="cyber-card p-5 border border-border"
            >
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle className="w-5 h-5 text-orange-400" />
                <h2 className="text-sm font-semibold text-foreground">
                  Incident Description
                </h2>
              </div>

              {/* Main textarea */}
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the security incident in detail...&#10;&#10;Example: Ransomware detected on finance workstations. Multiple files encrypted with .locked extension. Suspicious process 'svchost.exe' running from temp folder..."
                rows={6}
                disabled={isLoading}
                className="w-full bg-muted border border-border rounded-lg px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors disabled:opacity-60"
              />

              {/* Sample incidents */}
              {!description && (
                <div className="mt-2">
                  <p className="text-xs text-muted-foreground mb-2">
                    Try a sample:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {["Ransomware", "SSH Brute Force", "SQL Injection"].map(
                      (label, i) => (
                        <button
                          key={label}
                          onClick={() => setDescription(SAMPLE_INCIDENTS[i])}
                          className="px-2.5 py-1 text-xs border border-border rounded-md hover:border-primary/40 hover:text-primary text-muted-foreground transition-colors"
                        >
                          {label}
                        </button>
                      )
                    )}
                  </div>
                </div>
              )}

              {/* Optional fields toggle */}
              <button
                onClick={() => setShowOptional(!showOptional)}
                className="flex items-center gap-1.5 mt-4 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                <Info className="w-3.5 h-3.5" />
                {showOptional ? "Hide" : "Show"} optional fields
                {showOptional ? (
                  <ChevronUp className="w-3.5 h-3.5" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" />
                )}
              </button>

              <AnimatePresence>
                {showOptional && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="grid grid-cols-2 gap-3 mt-3 pt-3 border-t border-border">
                      <div>
                        <label className="text-xs text-muted-foreground mb-1 block">
                          Severity
                        </label>
                        <select
                          value={severity}
                          onChange={(e) => setSeverity(e.target.value)}
                          className="w-full cyber-input text-sm"
                          disabled={isLoading}
                        >
                          <option value="">Auto-detect</option>
                          <option value="critical">Critical</option>
                          <option value="high">High</option>
                          <option value="medium">Medium</option>
                          <option value="low">Low</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-xs text-muted-foreground mb-1 block">
                          Protocol
                        </label>
                        <input
                          type="text"
                          value={protocol}
                          onChange={(e) => setProtocol(e.target.value)}
                          placeholder="e.g. TCP, SSH, HTTP"
                          className="w-full cyber-input text-sm"
                          disabled={isLoading}
                        />
                      </div>
                      <div>
                        <label className="text-xs text-muted-foreground mb-1 block">
                          Source IP
                        </label>
                        <input
                          type="text"
                          value={sourceIp}
                          onChange={(e) => setSourceIp(e.target.value)}
                          placeholder="e.g. 192.168.1.1"
                          className="w-full cyber-input text-sm"
                          disabled={isLoading}
                        />
                      </div>
                      <div>
                        <label className="text-xs text-muted-foreground mb-1 block">
                          Destination IP
                        </label>
                        <input
                          type="text"
                          value={destIp}
                          onChange={(e) => setDestIp(e.target.value)}
                          placeholder="e.g. 10.0.0.1"
                          className="w-full cyber-input text-sm"
                          disabled={isLoading}
                        />
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Submit Button */}
              <div className="flex items-center gap-3 mt-5">
                <button
                  onClick={handleSubmit}
                  disabled={isLoading || !description.trim()}
                  className="flex items-center gap-2 px-5 py-2.5 bg-primary text-background rounded-lg text-sm font-semibold hover:bg-primary/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-[0_0_20px_rgba(0,212,255,0.4)]"
                >
                  <Play className="w-4 h-4" />
                  {isLoading ? "Analyzing..." : "Analyze Incident"}
                </button>

                {/* WebSocket status */}
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  {wsStatus === "connected" ? (
                    <>
                      <Wifi className="w-3.5 h-3.5 text-green-400" />
                      <span className="text-green-400">Live</span>
                    </>
                  ) : (
                    <>
                      <WifiOff className="w-3.5 h-3.5" />
                      <span>{wsStatus}</span>
                    </>
                  )}
                </div>
              </div>

              {/* Session ID */}
              {hasStarted && (
                <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground font-mono">
                  <span>Session:</span>
                  <span className="text-primary truncate max-w-48">
                    {sessionId}
                  </span>
                  <button
                    onClick={copySessionId}
                    className="hover:text-foreground transition-colors"
                  >
                    {copiedId ? (
                      <Check className="w-3.5 h-3.5 text-green-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              )}
            </motion.div>

            {/* Agent Timeline */}
            {hasStarted && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="cyber-card p-5 border border-border"
              >
                <AgentTimeline steps={agentSteps} isLoading={isLoading} />
              </motion.div>
            )}
          </div>

          {/* Right: Results Panel */}
          <AnimatePresence>
            {result && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="space-y-4"
              >
                {/* Classification Header */}
                <div className="cyber-card p-5 border border-border">
                  <div className="flex items-start justify-between mb-4">
                    <h2 className="text-sm font-semibold text-foreground">
                      Analysis Results
                    </h2>
                    <span className="text-xs text-muted-foreground">
                      {formatDate(result.created_at)}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <p className="text-xs text-muted-foreground mb-1.5">
                        Threat Class
                      </p>
                      <ThreatClassBadge threatClass={result.threat_class} />
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1.5">
                        Severity
                      </p>
                      <SeverityBadge
                        severity={
                          result.severity as
                            | "critical"
                            | "high"
                            | "medium"
                            | "low"
                        }
                      />
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1.5">
                        Escalation Level
                      </p>
                      <EscalationBadge
                        level={
                          result.escalation_level as "P1" | "P2" | "P3" | "P4"
                        }
                      />
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1.5">
                        Severity Score
                      </p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-muted rounded-full h-1.5 overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 rounded-full"
                            style={{
                              width: `${result.severity_score * 10}%`,
                            }}
                          />
                        </div>
                        <span className="text-sm font-bold text-foreground">
                          {result.severity_score}/10
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Summary */}
                  <div className="bg-muted rounded-lg p-3 mt-4">
                    <p className="text-xs text-muted-foreground mb-1">
                      Executive Summary
                    </p>
                    <p className="text-sm text-foreground leading-relaxed">
                      {result.summary}
                    </p>
                  </div>

                  {/* Escalation reason */}
                  {result.escalation_reason && (
                    <div className="mt-3 text-xs text-muted-foreground">
                      <span className="font-medium text-foreground">
                        Escalation reason:{" "}
                      </span>
                      {result.escalation_reason}
                    </div>
                  )}
                </div>

                {/* Mitigation Phases */}
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold text-foreground px-1">
                    Mitigation Plan
                  </h3>
                  {result.mitigation_phases.filter((p: MitigationPhase) => p.steps.length > 0).map(
                    (phase: MitigationPhase, i: number) => (
                      <AccordionItem
                        key={phase.phase || i}
                        title={
                          phaseLabels[phase.priority] ||
                          phase.title ||
                          phase.phase
                        }
                        defaultOpen={i === 0}
                        badge={phase.priority?.replace("_", " ")}
                        badgeColor={phaseBadgeColors[phase.priority] || ""}
                      >
                        <ul className="mt-3 space-y-2">
                          {phase.steps.map((step: string, j: number) => (
                            <li
                              key={j}
                              className="flex items-start gap-2.5 text-sm text-foreground"
                            >
                              <span className="text-primary font-mono font-medium shrink-0 mt-0.5">
                                {String(j + 1).padStart(2, "0")}.
                              </span>
                              <span className="leading-relaxed">{step}</span>
                            </li>
                          ))}
                        </ul>
                      </AccordionItem>
                    )
                  )}
                </div>

                {/* Similar Incidents */}
                {result.similar_incidents?.length > 0 && (
                  <div className="cyber-card p-5 border border-border">
                    <h3 className="text-sm font-semibold text-foreground mb-3">
                      Similar Incidents
                    </h3>
                    <div className="space-y-3">
                      {result.similar_incidents
                        .slice(0, 3)
                        .map((incident: SimilarIncident) => (
                          <div
                            key={incident.id}
                            className="p-3 rounded-lg bg-muted border border-border hover:border-primary/30 transition-colors cursor-pointer group"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex-1 min-w-0">
                                <p className="text-sm text-foreground truncate group-hover:text-primary transition-colors">
                                  {incident.title || incident.description}
                                </p>
                                <div className="flex items-center gap-2 mt-1">
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
                                  <ThreatClassBadge
                                    threatClass={incident.threat_class}
                                    className="text-xs"
                                  />
                                </div>
                              </div>
                              <div className="text-right shrink-0">
                                <div className="text-xs font-medium text-primary">
                                  {Math.round(incident.similarity_score * 100)}%
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  match
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {/* Judge Score */}
                <div className="cyber-card p-5 border border-border">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-foreground">
                        Quality Score
                      </h3>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {result.judge_feedback}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-3xl font-black text-primary">
                        {result.judge_score}
                        <span className="text-base text-muted-foreground font-normal">
                          /10
                        </span>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Judge score
                      </div>
                    </div>
                  </div>
                  <div className="mt-3 bg-muted rounded-full h-2 overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-primary to-accent rounded-full"
                      initial={{ width: "0%" }}
                      animate={{
                        width: `${(result.judge_score / 10) * 100}%`,
                      }}
                      transition={{ duration: 0.8, delay: 0.2 }}
                    />
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    Analysis completed in{" "}
                    <span className="text-primary font-mono">
                      {result.analysis_time_seconds?.toFixed(2) || "?"}s
                    </span>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Error State */}
            {error && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="cyber-card p-5 border border-destructive/30 bg-destructive/5"
              >
                <div className="flex items-center gap-2 text-destructive mb-2">
                  <AlertTriangle className="w-5 h-5" />
                  <h3 className="text-sm font-semibold">Analysis Failed</h3>
                </div>
                <p className="text-sm text-muted-foreground">{error}</p>
                <button
                  onClick={() => handleSubmit()}
                  className="mt-3 flex items-center gap-1.5 text-xs text-primary hover:text-primary/80 transition-colors"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Retry analysis
                </button>
              </motion.div>
            )}

            {/* Empty state */}
            {!hasStarted && (
              <div className="flex flex-col items-center justify-center h-64 text-center">
                <AlertTriangle className="w-12 h-12 text-muted-foreground/30 mb-4" />
                <p className="text-sm text-muted-foreground">
                  Analysis results will appear here
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Submit an incident description to get started
                </p>
              </div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </DashboardLayout>
  );
}
