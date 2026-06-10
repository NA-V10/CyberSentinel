# CyberSentinel AI — System Architecture

## Overview

CyberSentinel AI is a production-grade, multi-tenant SaaS cybersecurity incident response platform. It combines a Next.js 14 frontend, a FastAPI asynchronous backend, a Model Context Protocol (MCP) server, and a four-layer data stack (PostgreSQL, Qdrant, Neo4j, Redis) to deliver AI-powered incident triage, MITRE ATT&CK mapping, risk scoring, human-in-the-loop approval, and automated report generation — all streamed in real time.

---

## System Architecture — Text Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          BROWSER / ANALYST CLIENT                               │
│  /dashboard  /incidents  /war-room/{id}  /dashboard/executive  /simulation      │
│  /reports    /graph      /mcp-tools      /memory     /audit-logs  /feedback     │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │  HTTPS / WSS
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         NGINX REVERSE PROXY (:80 / :443)                        │
│            Routes /api/* → FastAPI :8000   /  → Next.js :3000                  │
└──────────────────┬────────────────────────────────────┬────────────────────────┘
                   │                                    │
         ┌─────────▼────────┐                ┌─────────▼───────────┐
         │  FastAPI Backend  │                │  Next.js 14 Frontend │
         │      :8000        │                │        :3000         │
         │                   │                │                      │
         │  ┌─────────────┐  │                │  Clerk Auth          │
         │  │ LangGraph   │  │◄───────────────│  Dashboard           │
         │  │ Multi-Agent │  │  REST + WS     │  Incident Analysis   │
         │  │ Workflow    │  │                │  War Room            │
         │  └──────┬──────┘  │                │  Executive Dash      │
         │         │         │                │  Graph View          │
         │  ┌──────▼──────┐  │                │  Simulation          │
         │  │  RAG / MITRE│  │                │  MCP Tools           │
         │  │  Risk / SLA │  │                │  Audit Logs          │
         │  └──────┬──────┘  │                └─────────────────────┘
         │         │         │
         │  ┌──────▼──────┐  │        ┌──────────────────────────┐
         │  │  Guardrails │  │        │    MCP Server :8001       │
         │  │  Memory     │  │◄───────│  stdio + HTTP transports  │
         │  │  WebSocket  │  │        │  Cybersecurity tool suite │
         │  └─────────────┘  │        └──────────────────────────┘
         └──────────┬────────┘
                    │
     ┌──────────────┼──────────────┬──────────────┐
     │              │              │              │
┌────▼────┐  ┌──────▼──────┐ ┌───▼────┐  ┌──────▼─────┐
│PostgreSQL│  │   Qdrant    │ │ Neo4j  │  │   Redis    │
│  :5432  │  │   :6333     │ │ :7687  │  │   :6379    │
│         │  │             │ │        │  │            │
│incidents│  │incident     │ │Incident│  │ML cache    │
│mitre_   │  │ embeddings  │ │Attack  │  │Session     │
│mappings │  │memory       │ │Type    │  │state       │
│approvals│  │ embeddings  │ │Asset   │  │            │
│audit_   │  │             │ │Mitig.  │  │            │
│sla_     │  │             │ │        │  │            │
│memory_  │  │             │ │        │  │            │
│feedback │  │             │ │        │  │            │
└─────────┘  └─────────────┘ └────────┘  └────────────┘
                                    │
                         ┌──────────▼──────────┐
                         │       OpenAI         │
                         │  GPT-4.1-mini        │
                         │  text-embedding-3-   │
                         │  small (1536-dim)    │
                         └─────────────────────┘
```

---

## Component Descriptions

### Frontend Layer (Next.js 14, :3000)

| Component | Path | Description |
|-----------|------|-------------|
| **Main Security Dashboard** | `/dashboard` | Incident volume charts, severity distribution (Recharts), recent incident feed, quick-action cards. Role-based rendering hides admin features from analyst accounts. |
| **SOC Executive Dashboard** | `/dashboard/executive` | Business-level KPIs for SOC leadership: MTTR, SLA breach rate, attack type distribution, analyst workload heatmap, trend comparisons. |
| **Incident Analysis** | `/incidents` | Primary analyst workspace. Submits incident text via POST then opens a WebSocket to stream live agent-step updates. Renders threat class, MITRE mapping, risk score, mitigation plan, escalation, explanation, and judge scorecard. |
| **Similar Incidents** | `/incidents/similar` | Hybrid RAG search interface for querying historical incidents by description, severity, or attack type. |
| **AI Incident War Room** | `/war-room/[incidentId]` | Realtime collaborative investigation workspace. Tabbed interface: Evidence Panel, MITRE ATT&CK tab, Risk Score gauge, Threat Intel enrichment, Agent Timeline, and Analyst Chat. |
| **Knowledge Graph View** | `/graph` | ReactFlow-powered interactive Neo4j subgraph visualisation. Nodes: Incident, AttackType, Asset, Mitigation. Edges: INCIDENT_OF_TYPE, TARGETS_ASSET, MITIGATED_BY, SIMILAR_TO. |
| **Reports** | `/reports` | Historical incident table (TanStack Table) with filtering, sorting, and pagination. One-click Markdown and PDF report download. |
| **Simulation Mode** | `/simulation` | Predefined attack scenario selector. Runs scenarios through the full agent pipeline in a sandboxed context. Results stream into the war room. |
| **MCP Tool Marketplace** | `/mcp-tools` | Browse, test, and manage MCP-exposed cybersecurity tools. Inline test runner with live response preview. |
| **Memory Bank** | `/memory` | View, search, and manage per-user, per-org, and per-incident memory scopes. |
| **Audit Logs** | `/audit-logs` | Tamper-evident log viewer for all analyst actions, AI decisions, and API calls. Admin-only. |
| **Analyst Feedback** | `/feedback` | Rating submission and feedback statistics dashboard. |
| **Clerk Auth** | `/sign-in`, `/sign-up` | Hosted Clerk authentication components with MFA support and organisation switching. |

### Backend Layer (FastAPI, :8000)

| Component | Description |
|-----------|-------------|
| **API Routers** | Seventeen FastAPI routers mounted under `/api/v1`: `analyze`, `mitre`, `approval`, `judge`, `dashboard`, `report`, `threat-intel`, `risk`, `feedback`, `guardrails`, `memory`, `playbook`, `simulation`, `sla`, `audit-logs`, `mcp`, and `ws`. |
| **LangGraph Workflow** | Compiled `StateGraph[AgentState]` with eight sequential agent nodes and conditional edges. Thread-safe singleton — handles concurrent requests with isolated per-invocation state dicts. |
| **RAG Pipeline** | `RAGPipeline` orchestrates `HybridRetriever` (Qdrant semantic + PostgreSQL FTS) and `GraphService.graph_rag_context` (Neo4j) to produce a formatted context string and `[REF-N]` citation list. |
| **MITRE ATT&CK Service** | Maps classified incidents to MITRE tactics (e.g., Impact), techniques (e.g., T1486), and sub-techniques. Maintains a local ATT&CK knowledge base supplemented by graph lookups. |
| **Risk Scoring Engine** | Explainable 0–100 composite score: `impact × 0.40 + likelihood × 0.35 + asset_criticality × 0.25`. Returns factor breakdown alongside the final score. |
| **Threat Intelligence Service** | Enriches IP addresses, domains, and file hashes via reputation APIs. Returns confidence classification (malicious / suspicious / clean) and enrichment metadata. |
| **Approval Service** | Manages the human-in-the-loop workflow states: `pending` → `approved` / `rejected` / `edited` / `escalated`. Persists all decisions to `incident_approvals` with analyst identity and timestamp. |
| **SLA Tracker** | Assigns SLA deadlines based on severity and escalation level. Monitors breach thresholds and triggers alert events. Persists to `sla_trackers`. |
| **Report Generator** | Produces Markdown and PDF incident reports from structured analysis output. PDFs are generated server-side via a headless renderer and signed with a report ID. |
| **Playbook Generator** | Creates customisable incident response playbooks from attack type, severity, MITRE mapping, and organisational context stored in memory. |
| **Memory Service** | Manages five memory scopes (user / incident / org / mitigation / false-positive) in Postgres and Qdrant. Supports semantic search and automatic procedural memory creation from analyst feedback. |
| **WebSocket Handler** | `ConnectionManager` singleton with per-session `asyncio.Lock` objects. Emits typed events: `validation`, `classification`, `retrieval`, `mitigation`, `escalation`, `explainability`, `judge`, `complete`, `error`. |
| **Guardrails Validator** | 19 prompt-injection patterns, offensive cyber action blocking, IP validation, text length bounds (10–5,000 chars), severity normalisation, and output credential sanitisation. |
| **ML Predictor** | RandomForest classifier on network flow features. Predictions cached in Redis (SHA-256 keyed, 30-minute TTL). Auto-trains from sample data if model artefact is absent at startup. |
| **Graph Service** | Async Neo4j driver wrapper. MERGE-based upserts for all node/relationship types. Concurrent Cypher queries for `graph_rag_context` and subgraph retrieval. |
| **Audit Logger** | Appends structured audit events to `audit_logs` on every significant analyst action, AI decision, approval change, and API call. Designed for SOC 2 / ISO 27001 compliance evidence. |

### MCP Server (:8001 / stdio)

The MCP server exposes cybersecurity tools over both stdio (Claude Desktop) and HTTP transports. All tools fall back gracefully to a static knowledge base when the backend is unreachable.

| Tool | Description |
|------|-------------|
| `search_similar_incidents` | Hybrid RAG search over historical incident knowledge base |
| `get_incident_by_id` | Full incident record retrieval by UUID |
| `get_attack_type_context` | MITRE-mapped attack type information and known patterns |
| `recommend_mitigation` | LLM-powered or KB-fallback four-phase mitigation plan |
| `calculate_risk_score` | Composite risk score: impact × 0.40 + likelihood × 0.35 + asset_criticality × 0.25 |
| `create_incident_report` | Structured report generation with executive summary and timeline |
| `query_graph_relationships` | Neo4j graph traversal for incident correlation |
| `store_feedback` | Analyst feedback submission and memory creation |

### Data Layer

| Store | Role |
|-------|------|
| **PostgreSQL** | Relational store for all structured data. Async access via SQLAlchemy + asyncpg. Schema migrations managed by Alembic. |
| **Qdrant** | Vector store for semantic search. Collections: `cybersentinel_incidents` (1536-dim incident embeddings) and `cybersentinel_memory` (user/org memory embeddings). Supports payload filtering at the index layer. |
| **Neo4j** | Property graph for knowledge representation and Graph RAG. Nodes: `Incident`, `AttackType`, `Asset`, `Protocol`, `Severity`, `Mitigation`. Enables structural context expansion and incident correlation. |
| **Redis** | Fast cache for ML prediction results (30-minute TTL), session state, and optional pub/sub for WebSocket fan-out. Degrades gracefully if unavailable. |

### LLM Layer (OpenAI)

| Model | Purpose |
|-------|---------|
| **gpt-4.1-mini** | All LLM calls: threat classification, mitigation generation, explanation writing, judge evaluation, MITRE mapping, playbook generation, report summarisation. JSON mode enforced for structured outputs. |
| **text-embedding-3-small** | 1536-dimensional dense vectors for incident texts and all memory entry types. Used at ingest time and at query time in the hybrid retriever. |

---

## Data Flow: End-to-End Incident Analysis

```
1. Analyst submits incident text via POST /api/v1/analyze/analyze-incident
   └─ Frontend simultaneously opens WS /api/v1/ws/war-room/{incident_id}

2. GUARDRAILS — ValidationAgent
   ├─ Prompt-injection pattern check (19 regex patterns)
   ├─ Offensive cyber blocking
   ├─ IP address format validation
   └─ Text length bounds (10–5,000 chars)
   [WS event: "Validating input..."]

3. MULTI-AGENT PIPELINE — LangGraph StateGraph
   │
   ├─ ClassificationAgent
   │   └─ GPT-4.1-mini → threat_class + confidence (JSON mode, temp=0.0)
   │   [WS event: "Classifying threat..."]
   │
   ├─ RetrievalAgent
   │   ├─ text-embedding-3-small → 1536-dim query vector
   │   ├─ Qdrant semantic search (top-K, filtered by severity/attack_type)
   │   ├─ PostgreSQL FTS (plainto_tsquery, ts_rank scored)
   │   ├─ Score fusion: 0.7 × semantic + 0.3 × keyword
   │   └─ Neo4j graph expansion (related incidents + MITIGATED_BY nodes)
   │   [WS event: "Searching similar incidents..."]
   │
   ├─ MITRE Mapping
   │   └─ Maps threat_class → MITRE tactic + technique + ATT&CK ID
   │   [WS event: "Mapping to MITRE ATT&CK..."]
   │
   ├─ MitigationAgent
   │   └─ GPT-4.1-mini → 4-phase plan (containment/eradication/recovery/prevention)
   │   [WS event: "Generating mitigation..."]
   │
   ├─ Risk Scoring Engine
   │   └─ Composite 0–100: impact × 0.40 + likelihood × 0.35 + asset_criticality × 0.25
   │   [WS event: "Calculating risk score..."]
   │
   ├─ Threat Intel Enrichment
   │   └─ IP reputation + domain classification + hash lookup
   │   [WS event: "Enriching threat intelligence..."]
   │
   ├─ EscalationAgent (rule-based)
   │   └─ L1 / L2 / L3 / SOC_Manager with SLA assignment
   │   [WS event: "Escalation level determined: L3"]
   │
   ├─ ExplainabilityAgent
   │   └─ GPT-4.1-mini → 3–5 paragraph professional explanation with citations
   │   [WS event: "Generating explanation..."]
   │
   └─ JudgeAgent (LLM-as-Judge)
       ├─ Scores: quality, safety, completeness, relevance, hallucination risk
       ├─ Retry loop: score < 5 or is_safe=false → re-run Mitigation + Explainability (max 1 retry)
       └─ [WS event: "Judge score: 8.9/10 | Safe: true"]

4. HUMAN-IN-THE-LOOP APPROVAL
   ├─ Approval record created in incident_approvals (status: pending)
   ├─ Analyst reviews judge scorecard in war room UI
   └─ Action: approve | reject | edit | escalate

5. REPORT GENERATION
   ├─ POST /api/v1/report/{id}/markdown → structured Markdown document
   └─ POST /api/v1/report/{id}/pdf     → signed PDF artefact

6. AUDIT + FEEDBACK
   ├─ All actions appended to audit_logs
   ├─ Analyst submits rating + mitigation effectiveness signal
   └─ Feedback stored for continuous learning
```

---

## Database Schema Overview

### `incidents`
Core incident records. Stores raw text, network metadata, AI-classified threat type, severity, and Qdrant embedding ID.

| Key Columns | Type | Description |
|-------------|------|-------------|
| `id` | UUID PK | Auto-generated incident UUID |
| `user_id` | VARCHAR | Clerk user ID of submitting analyst |
| `org_id` | VARCHAR | Clerk organisation ID (multi-tenant isolation) |
| `attack_type` | VARCHAR | AI-classified or manually specified attack type |
| `severity` | ENUM | low / medium / high / critical |
| `raw_text` | TEXT | Full incident description |
| `embedding_id` | VARCHAR | Corresponding Qdrant point UUID |
| `created_at` | TIMESTAMPTZ | Record creation timestamp |

### `mitre_mappings`
MITRE ATT&CK analysis results linked to incidents.

| Key Columns | Type | Description |
|-------------|------|-------------|
| `incident_id` | UUID FK | Parent incident |
| `tactic` | VARCHAR | MITRE tactic name (e.g., Impact, Execution) |
| `technique_id` | VARCHAR | ATT&CK technique ID (e.g., T1486) |
| `technique_name` | VARCHAR | Human-readable technique name |
| `confidence` | FLOAT | Mapping confidence score (0.0–1.0) |

### `incident_approvals`
Human-in-the-loop approval workflow state.

| Key Columns | Type | Description |
|-------------|------|-------------|
| `incident_id` | UUID FK | Parent incident |
| `status` | ENUM | pending / approved / rejected / edited / escalated |
| `analyst_id` | VARCHAR | Approving/rejecting analyst's Clerk user ID |
| `judge_scorecard` | JSON | Full LLM judge scorecard at time of review |
| `analyst_notes` | TEXT | Free-text notes from the reviewing analyst |
| `actioned_at` | TIMESTAMPTZ | Timestamp of the approval action |

### `audit_logs`
Tamper-evident append-only log of all significant platform events.

| Key Columns | Type | Description |
|-------------|------|-------------|
| `id` | UUID PK | Log entry UUID |
| `actor_id` | VARCHAR | Clerk user ID of the acting analyst |
| `org_id` | VARCHAR | Organisation scope |
| `event_type` | VARCHAR | Event category (incident_analyzed, approved, rejected, report_generated, etc.) |
| `resource_id` | VARCHAR | UUID of the affected resource |
| `payload` | JSON | Event-specific structured metadata |
| `created_at` | TIMESTAMPTZ | Event timestamp (append-only) |

### `sla_trackers`
SLA assignment and breach tracking per incident.

| Key Columns | Type | Description |
|-------------|------|-------------|
| `incident_id` | UUID FK | Parent incident |
| `escalation_level` | VARCHAR | L1 / L2 / L3 / SOC_Manager |
| `sla_deadline` | TIMESTAMPTZ | Calculated SLA deadline based on severity |
| `breached` | BOOLEAN | Whether the SLA was breached |
| `assigned_at` | TIMESTAMPTZ | SLA assignment timestamp |

### `memory_entries`
Analyst and organisation memory fragments for contextual recall.

| Key Columns | Type | Description |
|-------------|------|-------------|
| `id` | UUID PK | Memory entry UUID |
| `scope` | VARCHAR | user / incident / org / mitigation / false_positive |
| `owner_id` | VARCHAR | Clerk user ID or org ID depending on scope |
| `content` | TEXT | Plain-language memory fragment |
| `memory_type` | VARCHAR | episodic / semantic / procedural |
| `embedding_id` | VARCHAR | Qdrant point UUID for semantic search |

### `analyst_feedback`
Analyst rating and mitigation effectiveness signals.

| Key Columns | Type | Description |
|-------------|------|-------------|
| `incident_id` | UUID FK | Rated incident |
| `user_id` | VARCHAR | Submitting analyst |
| `rating` | INTEGER | 1 (poor) to 5 (excellent) |
| `mitigation_worked` | BOOLEAN | Whether the mitigation was effective |
| `comment` | TEXT | Free-text analyst notes |

### `conversations` and `messages`
Full conversation history between analysts and the AI workflow. Used for memory retrieval and audit.

---

## v2 Feature Architecture Details

### War Room WebSocket Flow

```
Analyst navigates to /war-room/{incident_id}
  └─ Frontend connects: WS /api/v1/ws/war-room/{incident_id}
       └─ ConnectionManager.connect(incident_id, websocket)
            └─ Per-step callbacks fire as each LangGraph agent completes:
                 {type: "status", step: "classification", message: "...", data: {...}}
                 {type: "status", step: "mitre", message: "T1486 mapped", data: {...}}
                 ...
                 {type: "complete", result: {full_analysis_object}}
```

The war room maintains a persistent WebSocket that can accept multiple simultaneous analyst connections (broadcast mode), enabling collaborative investigation without page refresh.

### MITRE + Graph RAG Hybrid Scoring

The hybrid reasoning layer fuses two independent scoring signals:

```
hybrid_score = (mitre_confidence × 0.45) + (graph_rag_similarity × 0.35) + (keyword_match × 0.20)
```

- **MITRE confidence**: Probability that the detected technique matches the observed behaviour patterns
- **Graph RAG similarity**: Cosine similarity of the incident embedding against known ATT&CK-mapped precedents in Neo4j
- **Keyword match**: Normalised PostgreSQL `ts_rank` against technique descriptions

The combined score drives both the MITRE technique confidence display and the overall risk score input.

### Risk Scoring Formula

```
risk_score (0–100) = (impact × 0.40) + (likelihood × 0.35) + (asset_criticality × 0.25)

Where:
  impact           = f(severity, attack_type, data_sensitivity)        → 0–100
  likelihood       = f(threat_confidence, historical_frequency)        → 0–100
  asset_criticality = f(affected_asset_tier, business_function)        → 0–100
```

The engine returns a complete factor breakdown alongside the scalar score, enabling the Explainability Panel to present a human-readable rationale.

### LLM Judge Pipeline

```
Analysis output assembled by AssembleFinal agent
  └─ JudgeAgent invokes GPT-4.1-mini with structured evaluation prompt:
       ├─ Correctness score (0–10): Does the mitigation address the threat?
       ├─ Safety score (boolean): No dangerous/offensive advice present?
       ├─ Completeness score (0–10): Are all four mitigation phases addressed?
       ├─ Relevance score (0–10): Is the response specific to the incident?
       └─ Hallucination risk (low/medium/high): Are claims grounded in retrieved evidence?
  └─ Composite quality score = mean(correctness, completeness, relevance) − hallucination_penalty
  └─ If quality < 5 or safety = false: retry_count < 1 → re-run Mitigation + Explainability
  └─ Judge scorecard persisted in incident_approvals for analyst review
```

### SLA Tracking Flow

```
EscalationAgent determines escalation_level
  └─ SLA Service assigns deadline based on org SLA policy:
       L1 → 4-hour response SLA
       L2 → 2-hour response SLA
       L3 → 1-hour response SLA
       SOC_Manager → 30-minute response SLA
  └─ SLA record created in sla_trackers
  └─ Background job polls breached SLAs every 5 minutes
  └─ Breach events emitted as WebSocket notifications to relevant analysts
  └─ Executive Dashboard aggregates SLA breach rate as a KPI
```

---

## Security Architecture

### Authentication and Authorisation
- All API endpoints require a valid Clerk JWT (except `/health` and ML prediction endpoints)
- JWTs validated against Clerk JWKS endpoint on every request; short-lived tokens limit replay attack exposure
- RBAC enforced at route level: `analyst` / `manager` / `admin` roles
- Organisation-level tenant isolation: `org_id` extracted from JWT and applied as a row-level filter on all database queries

### Guardrails and Input Safety
- 19 prompt-injection regex patterns compiled at startup
- Offensive cyber action detection blocks requests containing weaponisable instructions
- IP address validation using Python's `ipaddress` module (IPv4 and IPv6)
- Text length bounded (10–5,000 characters)
- All validation failures return HTTP 422 without consuming LLM tokens

### Output Security
- LLM outputs scanned for accidental credential leakage (API keys, JWTs, AWS credentials, private keys, GitHub PATs)
- Matched patterns replaced with `[REDACTED_*]` placeholders before API response delivery
- Judge safety flag independently confirms no harmful or offensive content

### Transport Security
- All production traffic uses HTTPS / WSS (TLS termination at Nginx)
- CORS origins restricted to configured production domains in non-debug mode
- WebSocket sessions keyed by UUID; JWT validated on connection establishment

### Audit and Compliance
- Append-only `audit_logs` table for SOC 2 / ISO 27001 evidence collection
- Every approval decision persisted with analyst identity, timestamp, and full scorecard
- Secure Audit Logs page provides tamper-evident log review for compliance officers

---

## Deployment Architecture — Docker Compose Services

| Service | Image | Port | Role |
|---------|-------|------|------|
| `postgres` | postgres:15 | 5432 | Primary relational database |
| `redis` | redis:7 | 6379 | Cache and session store |
| `qdrant` | qdrant/qdrant | 6333 / 6334 | Vector search engine |
| `neo4j` | neo4j:5 | 7474 / 7687 | Knowledge graph database |
| `backend` | custom (FastAPI) | 8000 | API server and agent orchestrator |
| `mcp-server` | custom (Python) | 8001 | MCP tool server |
| `frontend` | custom (Next.js) | 3000 | Web application |
| `nginx` | nginx:alpine | 80 / 443 | Reverse proxy and TLS termination |

All services declare health checks. The `backend` and `frontend` services depend on the database services being healthy before starting. Qdrant and Neo4j data directories are volume-mounted for persistence across container restarts.

---

## Technology Choices Rationale

### FastAPI over Django/Flask
FastAPI's native async support is essential for concurrent LLM calls, database queries, and WebSocket connections without thread-pool overhead. Pydantic v2 integration provides zero-cost request/response validation with automatic OpenAPI documentation.

### LangGraph for Agent Orchestration
LangGraph's `StateGraph` provides a typed, inspectable state machine for the multi-agent workflow. Conditional edges support the judge-retry loop without ad-hoc control flow. The compiled graph is thread-safe and reusable across concurrent requests.

### Hybrid RAG (Vector + Keyword + Graph)
Pure vector search misses exact terminology matches (IP addresses, CVE numbers, ATT&CK IDs, port numbers). PostgreSQL FTS fills that gap. Neo4j graph expansion adds structural knowledge — `brute_force MITIGATED_BY block-source-IP` — that neither vector nor keyword search can provide.

### MITRE ATT&CK Integration
The ATT&CK framework provides a universal taxonomy for threat communication. Mapping every incident to tactic/technique/ID enables: (a) cross-incident trend analysis by technique, (b) MITRE-guided mitigation recommendations, and (c) executive reporting in industry-standard terminology.

### Qdrant for Vector Storage
Qdrant supports rich payload filtering at query time without post-filtering — critical for scoped memory search and per-org tenant isolation. Multiple collections with independent configurations support the incident and memory use cases cleanly.

### Clerk for Authentication
Clerk provides production-grade JWT authentication with built-in React components, MFA, and organisation management. Organisation-level isolation enables multi-tenant SaaS without custom identity infrastructure.

### Neo4j for Knowledge Graph
The property graph model naturally represents cybersecurity ontologies. Cypher queries for related-incident lookup and MITRE-mapped mitigation retrieval are concise and performant. The graph grows organically with every ingested incident.

---

## Final Premium Feature Set — Architecture

### Updated System Diagram (Premium Layer)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          BROWSER / ANALYST CLIENT                               │
│  /dashboard  /incidents  /war-room/{id}  /campaigns  /digital-twin             │
│  /cost-intelligence  /campaigns/{id}  (+ all existing routes)                  │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │  HTTPS / WSS
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI BACKEND :8000                              │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                     EXISTING AGENT WORKFLOW (v2)                         │   │
│  │  Validation → Classification → Retrieval → Mitigation →                 │   │
│  │  Escalation → Explainability → Judge → AssembleFinal → Feedback          │   │
│  └─────────────────────────────┬────────────────────────────────────────────┘   │
│                                │                                                │
│  ┌─────────────────────────────▼────────────────────────────────────────────┐   │
│  │                   PREMIUM FEATURE LAYER (v3)                             │   │
│  │                                                                          │   │
│  │  SelfReflectionAgent    ──► POST /reflection/analyze                     │   │
│  │  (score < 7.5 → re-analyse, before/after comparison)                    │   │
│  │                                                                          │   │
│  │  CampaignDetectionService ► POST /campaigns/detect                       │   │
│  │  (O(n²) pairwise clustering: IP subnet + MITRE + attack type)            │   │
│  │                                                                          │   │
│  │  AutonomousInvestigationAgent ► POST /investigation/autonomous           │   │
│  │  (8 MCP tools: MITRE→IP→graph→similar→risk→mitigation→guardrails→report) │   │
│  │                                                                          │   │
│  │  ConsensusService      ──► POST /consensus/analyze                       │   │
│  │  (GPT 0.45 + Claude 0.35 + Llama 0.20, auto weight redistribution)      │   │
│  │                                                                          │   │
│  │  DigitalTwinService    ──► POST /digital-twin/run/{scenario_id}          │   │
│  │  (6 built-in scenarios, synthetic incidents, 85-95% accuracy scoring)    │   │
│  │                                                                          │   │
│  │  CostIntelligenceService ► GET /cost/summary|by-agent|by-model|savings   │   │
│  │  (per-call token tracking, Redis savings, optimisation suggestions)      │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└───────────────────┬─────────────────────────────────────────────────────────────┘
                    │
     ┌──────────────┼──────────────┬──────────────┐
     │              │              │              │
┌────▼────┐  ┌──────▼──────┐ ┌───▼────┐  ┌──────▼─────┐
│PostgreSQL│  │   Qdrant    │ │ Neo4j  │  │   Redis    │
│         │  │             │ │        │  │            │
│(+10 new │  │             │ │Campaign│  │Cost cache  │
│ tables) │  │             │ │Campaign│  │            │
└─────────┘  └─────────────┘ └────────┘  └────────────┘
```

### Premium Agent Flow

#### Self-Reflection Engine

```
LangGraph workflow completes → JudgeAgent assigns score
  └─► SelfReflectionAgent.should_reflect(state)
       ├─ judge_score >= 7.5 → "skip_reflection" (pass-through)
       └─ judge_score < 7.5  → "reflect"
            └─► _detect_weaknesses() [LLM call 1]
                 └─► _run_improved_analysis() [LLM call 2, includes weaknesses as context]
                      └─► _build_comparison() → before/after delta
                           └─► DB: self_reflections table
                                └─► WS: { type: "reflection", step: "complete", data: {...} }
```

#### Attack Campaign Detection

```
POST /campaigns/detect { incidents: [...], time_window_hours: 24 }
  └─► _cluster_incidents()
       ├─ For each pair (a, b):
       │   similarity = IP_subnet(0.25) + attack_type(0.25) + MITRE(0.25)
       │                + protocol(0.10) + severity(0.15)
       │   similarity >= 0.6 → same cluster
       └─ LLM campaign profiling → name, narrative, threat_actor_profile
            └─► DB: campaigns + campaign_incidents (join table)
```

#### Autonomous Investigation (8-Step MCP Pipeline)

```
POST /investigation/autonomous { incident_text, source_ip, severity }
  └─► Step 1: _tool_map_to_mitre()          → technique_id, tactic
  └─► Step 2: _tool_lookup_ip_reputation()   → verdict, tags
  └─► Step 3: _tool_query_threat_graph()     → related incidents (Neo4j)
  └─► Step 4: _tool_search_similar_incidents() → top-K similar
  └─► Step 5: _tool_calculate_risk()         → risk_score (0–100)
  └─► Step 6: _tool_recommend_mitigation()   → 4-phase plan
  └─► Step 7: _tool_check_guardrails()       → safety validation
  └─► Step 8: _tool_generate_report()        → structured summary
       └─► DB: autonomous_investigations + investigation_tool_calls
            └─► WS events per tool step: { type: "tool_call", tool: "...", sequence: N }
```

#### Multi-LLM Consensus

```
POST /consensus/analyze { incident_text }
  └─► Parallel execution:
       ├─ _analyze_with_openai()   weight 0.45
       ├─ _analyze_with_claude()   weight 0.35
       └─ _analyze_with_llama()    weight 0.20
  └─► _adjust_weights()  → redistribute proportionally for unavailable models
  └─► _compute_consensus()
       ├─ Weighted vote: classification (most weighted agreement wins)
       ├─ Weighted average: severity score
       └─ agreement_score = fraction of models aligned on final classification
  └─► DB: consensus_results + consensus_model_outputs
```

#### Digital Twin Simulator

```
GET /digital-twin/scenarios → 6 built-in scenarios + any org-custom scenarios

POST /digital-twin/run/{scenario_id}
  └─► _generate_synthetic_incidents(n=5)
       └─ Random IPs from scenario template subnet ranges
       └─ Attack names, protocols, asset types from template
  └─► _simulate_agent_response()
       └─ 85–95% correct classification (random sample)
       └─ Accuracy score + response quality score
  └─► DB: digital_twin_runs + nested agent_responses JSON
```

#### Cost Intelligence

```
Every service call (self-reflection, consensus, investigation, etc.):
  └─► cost_intelligence_service.log_usage(db,
        org_id, model_name, prompt_tokens, completion_tokens,
        workflow_name, agent_name, feature_name,
        cache_hit=True/False, cache_savings=...)
       └─► CostUsageLog row inserted
            └─► estimate_cost(model_name, p_tokens, c_tokens) using _COST_RATES dict

GET /cost/summary        → total_cost, total_tokens, avg_cost_per_call, date_range
GET /cost/by-agent       → cost breakdown per agent_name
GET /cost/by-model       → cost breakdown per model_name
GET /cost/by-workflow    → cost breakdown per workflow_name
GET /cost/by-user        → cost breakdown per user_id
GET /cost/savings        → redis_savings, memory_reuse_savings, total_savings
```

### New Database Tables

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `self_reflections` | id, org_id, incident_id, judge_score, reflection_triggered, weaknesses_detected, improved_analysis, final_confidence | Per-incident self-reflection records |
| `campaigns` | id, org_id, campaign_name, confidence, incident_count, mitre_techniques, attack_narrative, threat_actor_profile | Detected attack campaign groups |
| `campaign_incidents` | campaign_id, incident_id | Many-to-many campaign membership |
| `autonomous_investigations` | id, org_id, incident_id, status, tool_calls (JSON), evidence_chain (JSON), findings, judge_score, duration_seconds | Autonomous investigation runs |
| `investigation_tool_calls` | id, investigation_id, tool_name, sequence, duration_ms, input_params (JSON), output (JSON) | Per-tool invocation records |
| `consensus_results` | id, org_id, incident_id, consensus_classification, agreement_score, weights_used (JSON), final_recommendation | Multi-LLM consensus outputs |
| `consensus_model_outputs` | id, consensus_id, model_name, weight, classification, severity, confidence, key_findings | Per-model LLM output |
| `digital_twin_scenarios` | id, org_id, name, scenario_type, severity, expected_mitre_technique, incident_count | Scenario catalogue entries |
| `digital_twin_runs` | id, org_id, scenario_id, accuracy_score, response_quality_score, agent_responses (JSON) | Simulation run results |
| `cost_usage_logs` | id, org_id, user_id, model_name, agent_name, workflow_name, prompt_tokens, completion_tokens, estimated_cost, cache_savings, cache_hit, feature_name | Per-call cost/token records |

### New Frontend Routes (Premium)

| Route | Key Components |
|-------|---------------|
| `/war-room/[id]` → Self-Reflection tab | Confidence display, weakness list, missing evidence tags, before/after comparison cards, improvement suggestions |
| `/war-room/[id]` → Auto Investigation tab | Animated MCP tool call timeline (sequence + duration), evidence chain collapse, findings panel, final summary |
| `/war-room/[id]` → Consensus Engine tab | Per-model output row table (weight, classification, severity, confidence), agreement score radial, disagreement panel, final recommendation |
| `/campaigns` | Stats cards (active/total/avg confidence), search, campaign cards with confidence + status badges, "Detect Campaigns" button |
| `/campaigns/[campaignId]` | 4 tabs: Overview (narrative, threat actor, related incidents, MITRE, IPs, assets), Timeline (vertical event list), Indicators (shared IOCs + cluster stats), Response (recommended steps) |
| `/digital-twin` | 6 scenario cards (icon, difficulty badge, severity, incident count, MITRE); inline run result (accuracy bar, response quality, per-response dots) |
| `/cost-intelligence` | KPI cards, savings breakdown (Redis / Memory / RAG), BarChart by agent, PieChart by model, LineChart 14-day trend, optimisation suggestions table |
