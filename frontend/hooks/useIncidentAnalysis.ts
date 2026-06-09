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
  {
    id: "validation",
    name: "Validation Agent",
    description: "Validating incident description and extracting key indicators",
    status: "pending",
  },
  {
    id: "classification",
    name: "Classification Agent",
    description: "Classifying threat type and assigning severity score",
    status: "pending",
  },
  {
    id: "retrieval",
    name: "Retrieval Agent",
    description: "Searching similar incidents using RAG and knowledge graph",
    status: "pending",
  },
  {
    id: "mitigation",
    name: "Mitigation Agent",
    description: "Generating 4-phase mitigation plan",
    status: "pending",
  },
  {
    id: "escalation",
    name: "Escalation Agent",
    description: "Determining escalation level and priority",
    status: "pending",
  },
  {
    id: "summary",
    name: "Summary Agent",
    description: "Generating executive incident summary",
    status: "pending",
  },
  {
    id: "judge",
    name: "Judge Agent",
    description: "Evaluating response quality and completeness",
    status: "pending",
  },
  {
    id: "coordinator",
    name: "Coordinator Agent",
    description: "Assembling final response package",
    status: "pending",
  },
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

export function useIncidentAnalysis(): UseIncidentAnalysisReturn {
  const [sessionId, setSessionId] = useState<string>(() => generateSessionId());
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>(INITIAL_AGENT_STEPS);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wsEnabled, setWsEnabled] = useState(false);

  const updateAgentStep = useCallback(
    (agentId: string, updates: Partial<AgentStep>) => {
      setAgentSteps((prev) =>
        prev.map((step) =>
          step.id === agentId || step.name.toLowerCase().includes(agentId.toLowerCase())
            ? { ...step, ...updates }
            : step
        )
      );
    },
    []
  );

  const handleWsMessage = useCallback(
    (message: AgentMessage) => {
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
              startTime:
                message.status === "running" ? Date.now() : undefined,
              endTime:
                message.status === "complete" || message.status === "error"
                  ? Date.now()
                  : undefined,
              details: message.data,
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

        case "status":
          // General status update — ignore or log
          break;

        default:
          break;
      }
    },
    [updateAgentStep]
  );

  const { status: wsStatus } = useWebSocket({
    sessionId,
    onMessage: handleWsMessage,
    enabled: wsEnabled,
    onError: () => {
      // Fall back to polling if WebSocket fails
      console.warn("WebSocket failed, results will come from HTTP response");
    },
  });

  const submitIncident = useCallback(
    async (data: IncidentInput) => {
      // Reset state
      setAgentSteps(INITIAL_AGENT_STEPS.map((s) => ({ ...s, status: "pending" as AgentStatus })));
      setResult(null);
      setError(null);
      setIsLoading(true);

      // Generate new session ID for this analysis
      const newSessionId = generateSessionId();
      setSessionId(newSessionId);

      // Enable WebSocket connection
      setWsEnabled(true);

      try {
        const response = await apiClient.analyzeIncident({
          ...data,
          session_id: newSessionId,
        });

        // If we get a direct result (no WebSocket), use it
        if (response.data?.result) {
          setResult(response.data.result as AnalysisResult);
          setIsLoading(false);
          setWsEnabled(false);

          // Mark all steps as complete
          setAgentSteps((prev) =>
            prev.map((step) => ({ ...step, status: "complete" as AgentStatus }))
          );

          toast.success("Analysis complete!");
        }
        // If sessionId is returned, WebSocket will provide updates
      } catch (err: unknown) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to analyze incident";
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        const detail = axiosErr?.response?.data?.detail;

        setError(detail || errorMessage);
        setIsLoading(false);
        setWsEnabled(false);

        // Mark first running step as error
        setAgentSteps((prev) =>
          prev.map((step) =>
            step.status === "running" ? { ...step, status: "error" as AgentStatus } : step
          )
        );

        toast.error(detail || errorMessage);
      }
    },
    []
  );

  const reset = useCallback(() => {
    setSessionId(generateSessionId());
    setAgentSteps(INITIAL_AGENT_STEPS.map((s) => ({ ...s, status: "pending" as AgentStatus })));
    setResult(null);
    setError(null);
    setIsLoading(false);
    setWsEnabled(false);
  }, []);

  return {
    sessionId,
    agentSteps,
    result,
    isLoading,
    error,
    wsStatus,
    submitIncident,
    reset,
  };
}
