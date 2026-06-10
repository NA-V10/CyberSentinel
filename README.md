# CyberSentinel AI

> Enterprise AI-Powered Cybersecurity Incident Response Platform

CyberSentinel AI is a production-grade, multi-tenant SaaS platform that applies large-language-model reasoning, retrieval-augmented generation, MITRE ATT&CK mapping, and graph-based knowledge representation to cybersecurity incident triage and response. Submit a raw incident description and receive a fully structured analysis — threat classification, MITRE tactic/technique mapping, similar incident retrieval with citations, a four-phase mitigation playbook, risk scoring, human-in-the-loop approval, and a signed incident report — all streamed in real time to a collaborative war room workspace.

---

## Architecture Overview

| Layer | Components |
|-------|-----------|
| **Frontend** | Next.js 14 · TypeScript · Clerk authentication · Tailwind CSS · Framer Motion · ReactFlow · Recharts · TanStack Table |
| **Backend** | FastAPI (ASGI) · LangGraph multi-agent orchestration · Hybrid RAG pipeline · WebSocket streaming · Redis caching |
| **AI / ML** | OpenAI GPT-4.1-mini · text-embedding-3-small (1536-dim) · RandomForest ML classifier · LLM-as-Judge scorecard |
| **Data** | PostgreSQL 15+ (relational) · Qdrant (vector store) · Neo4j (knowledge graph) · Redis (cache + session) |
| **Security** | Clerk JWT · RBAC (analyst / manager / admin) · org-level tenant isolation · 19-pattern prompt-injection guardrails · output credential sanitisation |
| **Integrations** | MCP server (stdio + HTTP) · MITRE ATT&CK framework · threat intelligence enrichment (IP / domain / hash) |
| **Infrastructure** | Docker Compose · Nginx reverse proxy · Alembic migrations |

---

## Feature Highlights

### Core Platform
- **LangGraph Multi-Agent Workflow** — Eight specialised agents (validation, classification, retrieval, mitigation, escalation, explainability, judge, feedback) orchestrated as a compiled state machine with conditional retry logic
- **Hybrid RAG Retrieval** — Semantic search (Qdrant) + keyword search (PostgreSQL FTS) fused at 0.7 × semantic + 0.3 × keyword
- **Graph RAG with Neo4j** — Incident → AttackType → Mitigation → Asset knowledge graph with Cypher-based context expansion
- **LLM-as-Judge Validation** — Every response scored for quality, safety, completeness, and hallucination risk before delivery
- **Real-time WebSocket Streaming** — Live per-step agent progress pushed to the analyst UI as each agent completes
- **ML Threat Classifier** — RandomForest on network flow features (port, protocol, packet length, flow duration, packet rate) with Redis-cached predictions
- **MCP Server** — Cybersecurity tools exposed over stdio and HTTP; compatible with Claude Desktop and any MCP client
- **Clerk Authentication** — JWT-based auth with RBAC; multi-tenant org support via Clerk organisations
- **Memory System** — Five memory scopes (user / incident / org / mitigation / false-positive) stored in Postgres and indexed in Qdrant
- **Policy-Aware Guardrails** — 19 prompt-injection patterns + offensive cyber blocking + output credential sanitisation

### v2 Advanced Differentiators
1. **MITRE ATT&CK Mapping** — Every incident automatically mapped to tactic, technique, and ATT&CK ID (e.g., T1486 — Data Encrypted for Impact)
2. **AI Incident War Room** — Realtime collaborative investigation workspace at `/war-room/{id}` with evidence panels, live agent timeline, and analyst chat
3. **Human-in-the-Loop Approval** — Structured approve / reject / edit / escalate workflow before any mitigation is actioned
4. **LLM-as-Judge Scorecard** — Multi-dimensional quality validation: correctness, safety, completeness, relevance, and hallucination risk
5. **SOC Executive Dashboard** — Business-level KPIs at `/dashboard/executive`: MTTR, SLA breach rate, attack type distribution, analyst performance
6. **Auto Incident Report Generator** — One-click Markdown and PDF report generation with executive summary, timeline, and signed findings
7. **MITRE + Graph RAG Hybrid Reasoning** — Combined scoring formula fusing MITRE technique confidence with graph similarity scores
8. **Threat Intelligence Enrichment** — Automated IP reputation, domain classification, and file hash lookup via enrichment APIs
9. **Risk Scoring Engine** — Explainable 0–100 composite score: impact × 0.40 + likelihood × 0.35 + asset criticality × 0.25
10. **Continuous Feedback Learning** — Analyst rating and mitigation-effectiveness signals captured and stored for model improvement
11. **Policy-Aware Guardrails** — Offensive cyber action blocking; configurable per-org policy rules
12. **Advanced Memory Scopes** — Granular memory isolation: per-user, per-incident, per-org, mitigation history, false-positive registry
13. **Realtime WebSocket Agent Progress** — Per-step streaming with named agent nodes, percentage progress, and elapsed time
14. **Playbook Generator** — Automated, customisable incident response playbooks based on attack type and organisational context
15. **Simulation Mode** — `/simulation` — select a scenario (e.g., Ransomware Infection), run it through the full agent pipeline, and validate platform behaviour
16. **Explainability Panel** — Inline reasoning traces showing why each agent reached its decision
17. **Escalation SLA Tracker** — Automated SLA assignment, breach alerting, and escalation path visualisation
18. **Secure Audit Logs** — Tamper-evident, append-only audit log of all analyst actions, API calls, and AI decisions
19. **Multi-Tenant SaaS Support** — Clerk org isolation, per-org data scoping, and org-level memory stores
20. **MCP Tool Marketplace** — `/mcp-tools` — browse, test, and manage MCP-exposed cybersecurity tools from the UI

---

## Final Premium Feature Set

Six enterprise-grade capabilities added on top of the full v2 platform. Each feature has a dedicated backend service, FastAPI router, LangGraph agent node, frontend page or war-room tab, WebSocket events, multi-tenant isolation, audit logs, and mock fallbacks for keyless operation.

| # | Feature | Route(s) | Key Capability |
|---|---------|---------|----------------|
| 21 | **Agent Self-Reflection Engine** | `POST /reflection/analyze` · War Room tab | Post-judge self-critique loop: detects weaknesses, triggers re-analysis when judge score < 7.5, produces before/after comparison and final confidence score |
| 22 | **Attack Campaign Detection** | `POST /campaigns/detect` · `GET /campaigns` · `/campaigns/[id]` | O(n²) pairwise incident clustering by IP /24 subnet (0.25), attack type (0.25), MITRE (0.25), protocol (0.10), severity (0.15) — groups related incidents into named campaigns with confidence score and threat actor profile |
| 23 | **Autonomous Investigation Mode** | `POST /investigation/autonomous` · War Room tab | 8-step MCP tool pipeline: MITRE → IP reputation → graph → similar incidents → risk → mitigation → guardrails → report — returns full evidence chain, tool call timeline, and judge-scored summary |
| 24 | **Multi-LLM Consensus Engine** | `POST /consensus/analyze` · War Room tab | Parallel GPT (0.45) + Claude (0.35) + Llama (0.20) analysis; automatic weight redistribution when models unavailable; weighted voting for classification and severity; agreement score + disagreement summary |
| 25 | **AI SOC Digital Twin Simulator** | `GET /digital-twin/scenarios` · `POST /digital-twin/run/{id}` · `/digital-twin` | 6 built-in attack scenarios (phishing, malware, DDoS, insider, brute force, exfiltration); synthetic incident generation from templates; agent response simulation with 85–95% accuracy scoring |
| 26 | **Cost Intelligence Platform** | `GET /cost/summary|by-agent|by-model|by-user|by-workflow|savings` · `/cost-intelligence` | Per-call token and cost tracking across all agents and models; Redis cache savings calculation; memory reuse savings; 5 built-in optimisation suggestions; BarChart, PieChart, and LineChart visualisations |

### New Database Tables

| Table | Purpose |
|-------|---------|
| `self_reflections` | Per-incident reflection records: judge score, weaknesses, improved analysis, before/after comparison |
| `campaigns` | Detected attack campaigns with confidence score, narrative, threat actor profile, MITRE techniques |
| `campaign_incidents` | Many-to-many join between campaigns and constituent incidents |
| `autonomous_investigations` | Investigation runs: tool call sequence, evidence chain, timeline, findings, final summary |
| `investigation_tool_calls` | Individual MCP tool invocations within an investigation |
| `consensus_results` | Multi-LLM consensus outputs: model weights used, agreement score, disagreement summary |
| `consensus_model_outputs` | Per-model analysis from each LLM (classification, severity, confidence, key findings) |
| `digital_twin_scenarios` | Scenario definitions (overrides built-in catalogue for custom scenarios) |
| `digital_twin_runs` | Simulation run results: accuracy score, response quality, agent response records |
| `cost_usage_logs` | Per-call token and cost records: model, agent, workflow, user, prompt/completion tokens, estimated cost, cache savings |

### New Frontend Routes

| Route | Description |
|-------|-------------|
| `/war-room/[id]` (Self-Reflection tab) | Shows reflection trigger decision, weakness list, missing evidence, before/after comparison, final confidence |
| `/war-room/[id]` (Auto Investigation tab) | MCP tool call timeline with sequence numbers, evidence chain, findings panel, final summary |
| `/war-room/[id]` (Consensus Engine tab) | Per-model output table, agreement score cards, disagreement panel, weighted recommendation |
| `/campaigns` | Campaign list with stats cards, search, confidence badges, "Detect Campaigns" trigger |
| `/campaigns/[campaignId]` | 4-tab detail: Overview (narrative + threat actor + incidents), Timeline, Indicators, Response |
| `/digital-twin` | 6 scenario cards with difficulty badges; runs simulation and shows accuracy/quality scores inline |
| `/cost-intelligence` | KPI cards, savings breakdown, BarChart by agent, PieChart by model, LineChart trend, suggestions table |

### Architecture Update

```
┌─────────────────────────────────────────────────────────────────┐
│                    PREMIUM FEATURE LAYER                        │
│                                                                 │
│  SelfReflectionAgent  ──►  /reflection/analyze                  │
│  CampaignDetectionService ► /campaigns/detect                   │
│  AutonomousInvestigationAgent ► /investigation/autonomous       │
│  ConsensusService (GPT+Claude+Llama) ► /consensus/analyze       │
│  DigitalTwinService  ──►  /digital-twin/run/{id}                │
│  CostIntelligenceService ► /cost/summary                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Docker and Docker Compose | Latest stable |
| Python | 3.11+ |
| Node.js | 18+ |
| OpenAI API key | [platform.openai.com](https://platform.openai.com) |
| Clerk account | Free tier — [clerk.com](https://clerk.com) |

---

## Quick Start — Docker Compose

### 1. Clone and Configure

```bash
git clone https://github.com/your-org/cybersentinel-ai.git
cd cybersentinel-ai
cp .env.example .env
```

Edit `.env` with your credentials (see the Environment Variables table below).

### 2. Start All Services

```bash
docker compose up -d
```

Docker Compose starts PostgreSQL, Redis, Qdrant, Neo4j, the FastAPI backend, the MCP server, the Next.js frontend, and Nginx. All services are health-checked; the backend and frontend start only after the databases are ready.

Wait for the backend to complete its startup sequence:

```bash
docker compose logs -f backend | grep "Startup complete"
```

### 3. Ingest Dataset and Build Index

```bash
# Upload the sample incident dataset (requires admin Clerk token)
curl -X POST http://localhost:8000/api/v1/ingest/upload-csv \
  -F "file=@data/sample/sample_incidents.csv" \
  -H "Authorization: Bearer YOUR_CLERK_TOKEN"

# Build the Qdrant vector index over all ingested incidents
curl -X POST http://localhost:8000/api/v1/ingest/build-index \
  -H "Authorization: Bearer YOUR_CLERK_TOKEN"
```

### 4. Open the Platform

Navigate to [http://localhost:3000](http://localhost:3000) and sign in with your Clerk credentials.

---

## Manual Development Setup

### Backend

```bash
cd backend
pip install -r requirements.txt

# Start infrastructure only
docker compose up -d postgres redis qdrant neo4j

# Run the backend with live reload
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive API documentation is available at [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend development server starts at [http://localhost:3000](http://localhost:3000).

### MCP Server

```bash
cd mcp-server
pip install -r requirements.txt

# stdio transport (for Claude Desktop)
python server.py

# HTTP transport
python http_server.py
```

---

## Running Simulation Mode

1. Navigate to [http://localhost:3000/simulation](http://localhost:3000/simulation)
2. Select a predefined scenario (e.g., **Ransomware Infection**, **DDoS Volumetric Attack**, **Credential Stuffing**)
3. Click **Run Simulation**
4. Watch the multi-agent pipeline execute in the war room — each agent step streams in real time
5. Review the full analysis output including MITRE mapping, risk score, and generated playbook

Simulation mode is safe to use in production environments — it does not send traffic to external systems.

---

## Key API Examples

### Analyze an Incident

```bash
curl -X POST http://localhost:8000/api/v1/analyze/analyze-incident \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_CLERK_TOKEN" \
  -d '{
    "incident_text": "Multiple failed SSH login attempts from 192.168.1.25 to 10.0.0.5. Over 500 failed attempts in 10 minutes.",
    "severity": "High",
    "source_ip": "192.168.1.25",
    "dest_ip": "10.0.0.5",
    "protocol": "TCP"
  }'
```

### Map to MITRE ATT&CK

```bash
curl -X POST http://localhost:8000/api/v1/mitre/map \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_CLERK_TOKEN" \
  -d '{"incident_id": "YOUR_INCIDENT_UUID", "threat_class": "brute_force"}'
```

### Get Risk Score

```bash
curl -X POST http://localhost:8000/api/v1/risk/score \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_CLERK_TOKEN" \
  -d '{
    "incident_id": "YOUR_INCIDENT_UUID",
    "attack_type": "brute_force",
    "severity": "high",
    "affected_assets": ["10.0.0.5"],
    "historical_count": 12
  }'
```

### Generate Incident Report

```bash
# Markdown
curl -X POST http://localhost:8000/api/v1/report/YOUR_INCIDENT_UUID/markdown \
  -H "Authorization: Bearer YOUR_CLERK_TOKEN"

# PDF
curl -X POST http://localhost:8000/api/v1/report/YOUR_INCIDENT_UUID/pdf \
  -H "Authorization: Bearer YOUR_CLERK_TOKEN" --output report.pdf
```

---

## Frontend Walkthrough

| Step | Page | What You See |
|------|------|-------------|
| 1 | `/dashboard` | Incident volume, severity breakdown, attack type distribution, recent incident feed |
| 2 | `/incidents` | Submit a raw incident description; watch the live agent timeline stream in the war room |
| 3 | `/war-room/{id}` | Evidence panel, MITRE mapping tab, risk score gauge, threat intel enrichment panel |
| 4 | Approval panel | Judge scorecard (all dimensions 0–10), approve / reject / escalate workflow |
| 5 | `/reports` | Download the generated Markdown or PDF incident report |
| 6 | `/dashboard/executive` | SOC KPIs — MTTR, SLA breach rate, analyst workload distribution |
| 7 | `/simulation` | Select and run predefined attack scenarios end-to-end |
| 8 | `/mcp-tools` | Browse, test, and configure MCP-exposed cybersecurity tools |

---

## Panel Demo Flow (5 Steps)

1. **Submit incident** at `/incidents` — paste a ransomware description, click Analyze
2. **War room** — observe the per-step agent timeline; review MITRE T1486, risk score 87/100, threat intel IP reputation
3. **Human approval** — review the LLM judge scorecard; click Approve to action the mitigation
4. **Generate report** — click Generate Report; preview the Markdown; download the signed PDF
5. **Executive view** — navigate to `/dashboard/executive`; present MTTR, SLA compliance, and attack distribution to stakeholders

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Async PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Yes | Redis connection string (`redis://localhost:6379/0`) |
| `OPENAI_API_KEY` | Yes | OpenAI API key for chat completions and embeddings |
| `QDRANT_URL` | Yes | Qdrant server URL (`http://localhost:6333`) |
| `NEO4J_URI` | Yes | Neo4j Bolt URI (`bolt://localhost:7687`) |
| `NEO4J_USER` | Yes | Neo4j username |
| `NEO4J_PASSWORD` | Yes | Neo4j password |
| `CLERK_SECRET_KEY` | Yes | Clerk backend secret key (`sk_test_...`) |
| `CLERK_PUBLISHABLE_KEY` | Yes | Clerk publishable key (`pk_test_...`) |
| `NEXT_PUBLIC_API_URL` | Yes (frontend) | Backend API base URL (`http://localhost:8000`) |
| `NEXT_PUBLIC_WS_URL` | Yes (frontend) | Backend WebSocket base URL (`ws://localhost:8000`) |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Yes (frontend) | Clerk publishable key for Next.js |
| `OPENAI_CHAT_MODEL` | No | Chat model override (default: `gpt-4.1-mini`) |
| `OPENAI_EMBEDDING_MODEL` | No | Embedding model override (default: `text-embedding-3-small`) |
| `QDRANT_API_KEY` | No | Qdrant API key (required for Qdrant Cloud) |
| `ML_MODEL_PATH` | No | Path to trained RandomForest model file |
| `DEBUG` | No | Enable debug mode and wide CORS (default: `false`) |
| `API_V1_STR` | No | API version prefix (default: `/api/v1`) |

---

## License

MIT License — Copyright (c) 2026 CyberSentinel AI
