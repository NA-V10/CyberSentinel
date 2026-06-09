import axios, { AxiosInstance, AxiosError } from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_V1 = `${API_BASE}/api/v1`;

// Create axios instance pointing at the versioned API root
const api: AxiosInstance = axios.create({
  baseURL: API_V1,
  headers: { "Content-Type": "application/json" },
  timeout: 120000, // 2 min — LLM calls can be slow
});

// Token getter injected by AuthProvider once Clerk session is ready
let getToken: (() => Promise<string | null>) | null = null;

export function setTokenGetter(getter: () => Promise<string | null>) {
  getToken = getter;
}

// Inject Clerk JWT on every request
api.interceptors.request.use(
  async (config) => {
    if (getToken) {
      try {
        const token = await getToken();
        if (token) {
          config.headers = config.headers ?? {};
          config.headers.Authorization = `Bearer ${token}`;
        }
      } catch (err) {
        console.warn("Failed to get auth token:", err);
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Global error handler
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      const status = error.response.status;
      if (status === 401 && typeof window !== "undefined") {
        window.location.href = "/sign-in";
      }
    } else if (error.request) {
      console.error("Network error: backend unreachable at", API_V1);
    }
    return Promise.reject(error);
  }
);

// ---------------------------------------------------------------------------
// Typed API helpers — all paths are relative to /api/v1
// ---------------------------------------------------------------------------
export const apiClient = {
  // ---- Incident analysis ----
  analyzeIncident: (data: {
    description: string;
    severity?: string;
    source_ip?: string;
    destination_ip?: string;
    protocol?: string;
    session_id?: string;
  }) =>
    api.post("/analyze/analyze-incident", {
      incident_text: data.description,  // backend field name
      severity: data.severity,
      source_ip: data.source_ip,
      dest_ip: data.destination_ip,
      protocol: data.protocol,
      session_id: data.session_id,
    }),

  // ---- Search ----
  searchSimilar: (query: string, filters?: {
    attack_type?: string;
    severity?: string;
    protocol?: string;
    limit?: number;
  }) =>
    api.post("/search/similar", {
      query,
      ...filters,
      limit: filters?.limit ?? 10,
    }),

  // ---- Graph ----
  getIncidentGraph: (incidentId: string) =>
    api.get(`/graph/incident/${incidentId}`),

  getAttackTypeGraph: (attackType: string) =>
    api.get(`/graph/attack/${attackType}`),

  // ---- ML Prediction ----
  predictThreat: (data: {
    source_port: number;
    dest_port: number;
    protocol: string;
    packet_length: number;
    flow_duration: number;
    packet_rate?: number;
  }) => api.post("/predict-threat", data),

  getModelInfo: () => api.get("/predict-threat/model-info"),

  // ---- Ingest ----
  uploadCSV: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post("/ingest/upload-csv", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  buildIndex: () => api.post("/ingest/build-index"),

  // ---- Feedback ----
  submitFeedback: (data: {
    incident_id?: string;
    conversation_id?: string;
    rating: number;
    comment?: string;
    mitigation_worked?: boolean;
  }) => api.post("/feedback/", data),

  getFeedbackStats: () => api.get("/feedback/stats"),

  // ---- Memory / Conversations ----
  getConversations: (limit = 20) =>
    api.get("/memory/conversations", { params: { limit } }),

  getConversation: (id: string) =>
    api.get(`/memory/conversations/${id}`),

  deleteConversation: (id: string) =>
    api.delete(`/memory/conversations/${id}`),

  searchMemory: (query: string) =>
    api.post("/memory/search", { query }),

  // ---- Mitigation recommendation ----
  recommendMitigation: (data: {
    attack_type: string;
    severity: string;
    context?: string;
  }) => api.post("/recommend-mitigation", data),

  // ---- MITRE ATT&CK ----
  mapMITRE: (data: { attack_type: string; incident_text?: string; incident_id?: string }) =>
    api.post("/mitre/map", data),

  // ---- Human-in-the-Loop Approval ----
  getApprovalStatus: (incidentId: string) =>
    api.get(`/approval/${incidentId}`),
  submitApproval: (incidentId: string, action: "approve" | "reject" | "edit" | "regenerate" | "escalate", data?: Record<string, unknown>) =>
    api.post(`/approval/${incidentId}/${action}`, data || {}),

  // ---- LLM Judge ----
  judgeRecommendation: (data: { incident_text: string; recommendation: string; context?: Record<string, unknown> }) =>
    api.post("/judge/evaluate", data),

  // ---- Executive Dashboard ----
  getExecutiveMetrics: (days = 30) =>
    api.get("/dashboard/executive-metrics", { params: { days } }),

  // ---- Threat Intelligence ----
  enrichIndicator: (data: { ip?: string; domain?: string; file_hash?: string }) =>
    api.post("/threat-intel/enrich", data),

  // ---- Risk Scoring ----
  calculateRisk: (data: { severity: string; attack_type: string; source_ip?: string; model_confidence?: number }) =>
    api.post("/risk/score", data),

  // ---- Playbook ----
  generatePlaybook: (data: { attack_type: string; severity: string; incident_text?: string; source_ip?: string }) =>
    api.post("/playbook/generate", data),

  // ---- Simulation ----
  getScenarios: () => api.get("/simulation/scenarios"),
  runScenario: (scenarioId: string) => api.post(`/simulation/run/${scenarioId}`),

  // ---- SLA ----
  assignSLA: (incidentId: string, severity: string) =>
    api.post("/sla/assign", { incident_id: incidentId, severity }),
  getSLAStatus: (incidentId: string) =>
    api.get(`/sla/${incidentId}`),
  resolveSLA: (incidentId: string) =>
    api.post(`/sla/${incidentId}/resolve`),

  // ---- Audit Logs ----
  getAuditLogs: (params?: { limit?: number; offset?: number; event_type?: string; user_id?: string }) =>
    api.get("/audit-logs/", { params }),

  // ---- MCP Tools ----
  getMCPTools: () => api.get("/mcp/tools"),
  testMCPTool: (toolName: string, input?: Record<string, unknown>) =>
    api.post(`/mcp/tools/${toolName}/test`, { input }),

  // ---- Health ----
  healthCheck: () =>
    axios.get(`${API_BASE}/health`),  // health is at root, not /api/v1
};

// WebSocket helper — builds the correct WS URL for the agent pipeline
export function buildWsUrl(sessionId: string): string {
  const wsBase = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
  return `${wsBase}/api/v1/ws/analyze/${sessionId}`;
}

// War Room WebSocket helper
export function buildWarRoomWsUrl(incidentId: string): string {
  const wsBase = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
  return `${wsBase}/api/v1/ws/war-room/${incidentId}`;
}

export default api;
