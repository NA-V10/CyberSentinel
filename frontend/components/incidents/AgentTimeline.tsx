"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  ChevronDown,
  ChevronUp,
  Brain,
  Search,
  Shield,
  AlertTriangle,
  FileText,
  Star,
  Layers,
  Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentStep, AgentStatus } from "@/hooks/useIncidentAnalysis";

const agentIcons: Record<string, React.ElementType> = {
  validation: Shield,
  classification: AlertTriangle,
  retrieval: Search,
  mitigation: Layers,
  escalation: Activity,
  summary: FileText,
  judge: Star,
  coordinator: Brain,
};

const agentColors: Record<string, string> = {
  validation: "text-blue-400 border-blue-400/30 bg-blue-400/10",
  classification: "text-orange-400 border-orange-400/30 bg-orange-400/10",
  retrieval: "text-cyan-400 border-cyan-400/30 bg-cyan-400/10",
  mitigation: "text-green-400 border-green-400/30 bg-green-400/10",
  escalation: "text-red-400 border-red-400/30 bg-red-400/10",
  summary: "text-purple-400 border-purple-400/30 bg-purple-400/10",
  judge: "text-yellow-400 border-yellow-400/30 bg-yellow-400/10",
  coordinator: "text-primary border-primary/30 bg-primary/10",
};

interface AgentTimelineProps {
  steps: AgentStep[];
  isLoading?: boolean;
}

function StatusIcon({ status }: { status: AgentStatus }) {
  switch (status) {
    case "complete":
      return <CheckCircle2 className="w-5 h-5 text-green-400" />;
    case "error":
      return <XCircle className="w-5 h-5 text-red-400" />;
    case "running":
      return <Loader2 className="w-5 h-5 text-primary animate-spin" />;
    case "pending":
    default:
      return <Clock className="w-5 h-5 text-muted-foreground" />;
  }
}

function AgentStepItem({ step, index }: { step: AgentStep; index: number }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const IconComponent = agentIcons[step.id] || Brain;
  const colorClass = agentColors[step.id] || "text-primary border-primary/30 bg-primary/10";
  const isActive = step.status === "running";
  const isComplete = step.status === "complete";
  const isError = step.status === "error";
  const isPending = step.status === "pending";

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className={cn(
        "relative border rounded-lg overflow-hidden transition-all duration-300",
        isActive && "border-primary/50 bg-primary/5 shadow-[0_0_15px_rgba(0,212,255,0.1)]",
        isComplete && "border-green-500/30 bg-green-500/5",
        isError && "border-red-500/30 bg-red-500/5",
        isPending && "border-border bg-card/50 opacity-60"
      )}
    >
      {/* Running pulse */}
      {isActive && (
        <div className="absolute inset-0 bg-primary/5 animate-pulse pointer-events-none" />
      )}

      <button
        onClick={() => !isPending && setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-3 p-3 text-left"
        disabled={isPending}
      >
        {/* Agent icon */}
        <div
          className={cn(
            "w-9 h-9 rounded-lg border flex items-center justify-center shrink-0",
            colorClass
          )}
        >
          <IconComponent className="w-4 h-4" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "text-sm font-medium",
                isPending ? "text-muted-foreground" : "text-foreground"
              )}
            >
              {step.name}
            </span>
            {isActive && (
              <span className="text-xs text-primary font-mono animate-pulse">
                RUNNING
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground truncate mt-0.5">
            {step.message || step.description}
          </p>
        </div>

        {/* Status icon */}
        <div className="flex items-center gap-2 shrink-0">
          <StatusIcon status={step.status} />
          {!isPending && step.details && (
            <span className="text-muted-foreground">
              {isExpanded ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </span>
          )}
        </div>
      </button>

      {/* Expanded details */}
      <AnimatePresence>
        {isExpanded && step.details && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t border-border overflow-hidden"
          >
            <div className="p-3 space-y-2">
              {Object.entries(step.details).map(([key, value]) => (
                <div key={key} className="flex items-start gap-2 text-xs">
                  <span className="text-muted-foreground capitalize shrink-0 w-32">
                    {key.replace(/_/g, " ")}:
                  </span>
                  <span className="text-foreground font-mono break-all">
                    {typeof value === "object"
                      ? JSON.stringify(value, null, 2)
                      : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Progress indicator for running */}
      {isActive && (
        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-muted overflow-hidden">
          <motion.div
            className="h-full bg-primary"
            animate={{ x: ["-100%", "100%"] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
          />
        </div>
      )}
    </motion.div>
  );
}

export function AgentTimeline({ steps, isLoading }: AgentTimelineProps) {
  const completedCount = steps.filter((s) => s.status === "complete").length;
  const totalCount = steps.length;
  const progress = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

  return (
    <div className="space-y-3">
      {/* Progress header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-primary" />
          <h3 className="text-sm font-semibold text-foreground">
            AI Agent Pipeline
          </h3>
        </div>
        <div className="flex items-center gap-2">
          {isLoading && (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            >
              <Loader2 className="w-4 h-4 text-primary" />
            </motion.div>
          )}
          <span className="text-xs text-muted-foreground font-mono">
            {completedCount}/{totalCount} complete
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-muted rounded-full h-1.5 mb-4 overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-primary to-secondary rounded-full"
          initial={{ width: "0%" }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>

      {/* Agent steps */}
      <div className="space-y-2">
        {steps.map((step, index) => (
          <AgentStepItem key={step.id} step={step} index={index} />
        ))}
      </div>

      {/* Summary row */}
      <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
            {steps.filter((s) => s.status === "complete").length} Done
          </span>
          <span className="flex items-center gap-1">
            <Loader2 className="w-3.5 h-3.5 text-primary" />
            {steps.filter((s) => s.status === "running").length} Running
          </span>
          <span className="flex items-center gap-1">
            <XCircle className="w-3.5 h-3.5 text-red-400" />
            {steps.filter((s) => s.status === "error").length} Errors
          </span>
        </div>
        {progress === 100 && (
          <span className="text-green-400 font-medium">Pipeline Complete</span>
        )}
      </div>
    </div>
  );
}

export default AgentTimeline;
