# CyberSentinel AI — Design Document

**Version:** 1.0.0  
**Date:** 2026-06-08  
**Authors:** CyberSentinel AI Engineering Team

---

## 1. Executive Summary

CyberSentinel AI is a production-grade SaaS platform that applies large-language-model reasoning, retrieval-augmented generation, and graph-based knowledge representation to cybersecurity incident response. It ingests raw incident descriptions from security analysts, runs them through an eight-agent LangGraph workflow, and returns a structured analysis comprising threat classification, similar incident retrieval with citations, a four-phase mitigation plan (containment / eradication / recovery / prevention), an escalation decision (L1 / L2 / L3 / SOC_Manager), a natural-language explanation, and a LLM-as-Judge quality score — all streamed in real time via WebSockets.

The system is designed for security operations centres (SOCs) and managed security service providers (MSSPs) that need AI-assisted triage without sacrificing interpretability, auditability, or safety.

---

## 2. Problem Statement

Modern security operations centres face several compounding challenges:

- **Alert volume**: Enterprise SIEMs generate thousands of alerts per day; the vast majority are false positives or low-priority events that consume analyst time.
- **Knowledge silos**: Institutional knowledge about how similar incidents were handled in the past is trapped in Slack threads, ticket comments, and individual analyst memory.
- **Slow triage**: Manual incident analysis — reading logs, looking up IP reputation, drafting mitigation steps — can take 30–90 minutes per incident.
- **Inconsistent escalation**: Junior analysts apply escalation criteria inconsistently, leading to both under-escalation (missed critical incidents) and over-escalation (SOC manager fatigue).
- **No feedback loop**: Analyst assessments of AI suggestions are rarely captured in a structured way that could improve future recommendations.

CyberSentinel AI addresses each of these directly: it automates the triage workflow, retrieves historical precedents, generates consistent escalation decisions, and captures analyst feedback to improve over time.

---

## 3. Solution Overview

CyberSentinel AI provides:

1. **Hybrid incident search** — semantic (Qdrant dense vectors) + keyword (PostgreSQL full-text) + graph (Neo4j relationship traversal) retrieval over a historical incident knowledge base.
2. **Multi-agent AI workflow** — an eight-node LangGraph state machine that processes each incident through specialised agents, each with a defined responsibility and fallback behaviour.
3. **Real-time streaming** — FastAPI WebSocket connections push live agent-step status updates to the analyst UI as the workflow progresses.
4. **Graph-augmented knowledge** — Neo4j stores structural relationships between incidents, attack types, assets, protocols, severities, and mitigations, enabling Graph RAG context expansion.
5. **ML threat prediction** — a RandomForest classifier trained on network flow features provides a second opinion alongside the LLM classification.
6. **In-app memory** — per-user episodic, semantic, and procedural memory stored in Postgres and indexed in Qdrant, enabling personalised context recall.
7. **LLM-as-Judge validation** — every generated response is evaluated by a second LLM call that scores quality (0–10), safety, completeness, and hallucination risk before delivery.
8. **MCP server** — a Model Context Protocol server exposing eight cybersecurity tools over stdio and HTTP transports, enabling integration with Claude Desktop and other MCP clients.

---

## 4. System Architecture

Refer to [`architecture.md`](./architecture.md) for the full Mermaid system diagram, component descriptions, data flow sequence diagram, agent workflow diagram, RAG pipeline diagram, and technology choices rationale.

**High-level topology:**

```
Browser → Next.js 14 (Clerk auth) → FastAPI :8000 → LangGraph workflow
                                          ↓
                                   Qdrant (vectors)
                                   PostgreSQL (relational)
                                   Neo4j (knowledge graph)
                                   Redis (cache)
                                   OpenAI (LLM + embeddings)
```

---

## 5. Core Components

### 5.1 Authentication (Clerk JWT)

CyberSentinel AI uses Clerk for identity management. The Next.js frontend renders Clerk's hosted sign-in and sign-up components at `/sign-in` and `/sign-up`. After authentication, Clerk issues a JWT that is forwarded as a `Bearer` token in all API requests.

The FastAPI backend validates the JWT by fetching the Clerk JWKS endpoint (`CLERK_JWT_ISSUER`) and verifying the signature, expiry, and issuer claims. User identity (`user_id`) and role (`analyst`, `manager`, `admin`) are extracted from the token payload and injected into every route handler via the `get_current_user` dependency.

**Role matrix:**

| Role | Capabilities |
|------|-------------|
| `analyst` | Analyze incidents, search, view graph, submit feedback, read own memory |
| `manager` | All analyst capabilities + view all users' incidents and feedback stats |
| `admin` | All capabilities + ingest data (upload CSV, build index), manage system settings |

### 5.2 Data Ingestion Pipeline

Incidents enter the system through two paths:

**Batch CSV ingestion** (`POST /api/v1/ingest/upload-csv`, admin only):
1. Parse the uploaded CSV; required column: `raw_text`. Optional: `source_ip`, `dest_ip`, `protocol`, `attack_type`, `severity`, `label`, `timestamp`.
2. Validate and normalise each row (severity must be one of: low, medium, high, critical).
3. Bulk-insert `Incident` records into PostgreSQL via SQLAlchemy async session.
4. Embed all `raw_text` values in batches of 50 using `text-embedding-3-small`.
5. Upsert each embedding + payload into Qdrant collection `cybersentinel_incidents`.
6. Create Neo4j nodes (`Incident`) and relationships (`INCIDENT_OF_TYPE`, `TARGETS_ASSET`, `USES_PROTOCOL`, `HAS_SEVERITY`) for each incident.

**Re-indexing** (`POST /api/v1/ingest/build-index`, admin only):
Re-embeds every incident in the database and upserts into Qdrant. Used after changing the embedding model or clearing the vector store.

**Live ingestion** (via Feedback Agent):
Every incident analysed through the workflow is automatically persisted as a new `Incident` record plus a `Conversation` with `Message` records.

### 5.3 RAG Pipeline (Hybrid: Vector + Keyword + Graph)

The `RAGPipeline` class orchestrates three complementary retrieval strategies:

**Step 1 — Hybrid Retrieval (`HybridRetriever`)**

The `HybridRetriever` runs semantic and keyword search concurrently:

- **Semantic search**: Embeds the query with `text-embedding-3-small` → queries Qdrant with optional metadata filters (attack_type, severity, protocol) → returns top-K results with cosine similarity scores.
- **Keyword search**: Executes a parameterised PostgreSQL query using `to_tsvector` / `plainto_tsquery` with optional WHERE clauses for severity, attack_type, and protocol → uses `ts_rank` as the score.

Results are fused using weighted score fusion:
```
fused_score = 0.7 × semantic_score + 0.3 × keyword_score
```
Keyword scores are min-max normalised to [0, 1] before fusion. Duplicate hits (appearing in both result sets) receive both weights.

**Step 2 — Graph Expansion (`GraphService.graph_rag_context`)**

Using the top-ranked attack type from Step 1, the pipeline queries Neo4j concurrently for:
- Related incidents sharing the same `AttackType` node (up to 5).
- Known `Mitigation` nodes connected via `MITIGATED_BY` relationships.

**Step 3 — Context Formatting and Citations**

Results are formatted into a structured text block with `[REF-N]` citation markers. Citations include: incident ID, title, severity, attack type, similarity score, and creation timestamp. The formatted context is injected into all downstream LLM prompts.

### 5.4 LangGraph Multi-Agent Workflow

The workflow is a compiled `StateGraph[AgentState]` with nine nodes and two conditional edge sets. It is compiled once at module load time and reused concurrently across requests. The shared state (`AgentState`, a TypedDict) is passed between nodes as immutable partial updates.

**Agent descriptions:**

| Agent | Node Name | Responsibility | LLM Call |
|-------|-----------|----------------|----------|
| **ValidationAgent** | `validation` | Validates incident text length (10–5,000 chars), IP address format, prompt-injection patterns. Routes to END on failure. | None |
| **ClassificationAgent** | `classification` | Classifies the incident into one of seven threat classes (phishing, malware, ddos, brute_force, unauthorized_access, network_intrusion, benign) with confidence score. Uses JSON mode. | GPT-4.1-mini, temperature=0.0 |
| **RetrievalAgent** | `retrieval` | Runs the full hybrid RAG pipeline (HybridRetriever + GraphService.graph_rag_context). Falls back to semantic-only if DB session is unavailable. Populates similar_incidents, graph_context, rag_context, citations. | Embedding: text-embedding-3-small |
| **MitigationAgent** | `mitigation` | Generates a four-phase response plan (containment, eradication, recovery, prevention) using the RAG context. Falls back to a hardcoded knowledge base keyed by threat class if the LLM call fails or the JSON output is invalid. | GPT-4.1-mini, temperature=0.2 |
| **EscalationAgent** | `escalation` | Rule-based decision matrix using threat_class, threat_confidence, severity weight, and similar_count. Produces levels L1 / L2 / L3 / SOC_Manager with a human-readable reason string. | None |
| **ExplainabilityAgent** | `explainability` | Writes a 3–5 paragraph professional explanation covering classification rationale, risk indicators, escalation justification, and response summary. Uses all prior state fields. | GPT-4.1-mini, temperature=0.3 |
| **JudgeAgent** | `judge` | LLM-as-Judge: evaluates quality (0–10), safety (boolean), completeness (0–10), and hallucination risk (low/medium/high). Scores < 5 or is_safe=false trigger one retry of the mitigation + explainability cycle. Falls back to rule-based scoring if LLM call fails. | GPT-4.1-mini, temperature=0.0 |
| **AssembleFinal** | `assemble_final` | Serialises all state fields into the `final_answer` JSON string. | None |
| **FeedbackAgent** | `feedback` | Asynchronously persists the Conversation, Messages, and Incident records to PostgreSQL using `asyncio.ensure_future`. Non-blocking — does not add latency to the response. | None |

**Retry logic:** The judge node can route back to `mitigation` once if the response fails quality or safety checks (`retry_count < 1`). This prevents infinite loops while allowing one regeneration attempt.

### 5.5 MCP Server (Model Context Protocol)

The MCP server (`mcp-server/server.py`) runs as a standalone process supporting both stdio transport (for Claude Desktop) and HTTP transport (`http_server.py`). It exposes eight tools and three resource endpoints.

**Tools:**

| Tool | Inputs | Purpose |
|------|--------|---------|
| `search_similar_incidents` | query, severity?, attack_type?, limit? | Hybrid RAG search over historical incidents |
| `get_incident_by_id` | incident_id | Full record retrieval by UUID |
| `get_attack_type_context` | attack_type | MITRE-mapped patterns, affected systems, ports, tactics |
| `recommend_mitigation` | attack_type, severity, context? | LLM-powered or KB-fallback four-phase mitigation |
| `calculate_risk_score` | attack_type, severity, affected_assets, historical_count? | Weighted composite risk score (0–100): impact × 0.40 + likelihood × 0.35 + asset_criticality × 0.25 |
| `create_incident_report` | incident_data{} | Structured report with executive summary, technical details, timeline, mitigation plan |
| `query_graph_relationships` | incident_id?, attack_type? | Neo4j graph traversal — nodes and edges |
| `store_feedback` | incident_id, rating, mitigation_worked, comment? | Analyst feedback submission |

**Resources:**

| URI | Description |
|-----|-------------|
| `cybersentinel://incidents/recent` | 10 most recently ingested incidents |
| `cybersentinel://attack-types` | Full attack-type catalog with MITRE tactics |
| `cybersentinel://mitigations` | All mitigation playbook templates by attack type |

All tools include graceful fallback to the built-in static knowledge base when the backend API is unreachable.

### 5.6 Graph RAG with Neo4j

Neo4j stores the cybersecurity knowledge graph with the following schema:

**Node labels:**
- `Incident` — properties: incident_id, user_id, attack_type, severity, created_at
- `AttackType` — properties: name
- `Asset` — properties: ip
- `Protocol` — properties: name
- `Severity` — properties: level
- `Mitigation` — properties: description

**Relationship types:**
- `(Incident)-[:INCIDENT_OF_TYPE]->(AttackType)`
- `(Incident)-[:TARGETS_ASSET {role: source|destination}]->(Asset)`
- `(Incident)-[:USES_PROTOCOL]->(Protocol)`
- `(Incident)-[:HAS_SEVERITY]->(Severity)`
- `(AttackType)-[:MITIGATED_BY]->(Mitigation)`
- `(Incident)-[:SIMILAR_TO {score: float}]->(Incident)`

At ingestion time, each incident creates nodes and all relevant relationships using Cypher `MERGE` to avoid duplicates. At analysis time, the `graph_rag_context` method fetches related incidents (via the shared AttackType node) and known mitigations in two concurrent async Cypher queries.

The frontend Graph View component uses the `/api/v1/search/incident/{id}` endpoint to fetch a JSON nodes+edges representation and renders it with ReactFlow, allowing analysts to visually explore incident relationships.

### 5.7 ML Threat Prediction

The ML subsystem provides a statistical second opinion alongside the LLM classification:

**Model:** RandomForestClassifier (scikit-learn) with XGBoost as an optional alternative.

**Features:**
| Feature | Description |
|---------|-------------|
| `source_port` | Source TCP/UDP port number |
| `dest_port` | Destination port number |
| `protocol_encoded` | Protocol as integer (TCP=0, UDP=1, ICMP=2, HTTP=3, HTTPS=4, DNS=5, SSH=6, FTP=7) |
| `packet_length` | Average packet size in bytes |
| `flow_duration` | Total flow duration in milliseconds |
| `packet_rate` | Packets per second |

**Output:** Predicted threat class, confidence (top-class probability), all class probabilities, feature importance sorted descending.

**Caching:** Predictions are cached in Redis for 30 minutes using a SHA-256 hash of the feature dict as the key, eliminating redundant model inference for duplicate network flows.

**Training:** The `trainer.py` module trains on the sample dataset at `data/sample/sample_incidents.csv` and serialises the artefact (model, label_encoder, feature_names, metrics) to `models/threat_classifier.joblib`. If the model file is missing at startup, training runs automatically.

### 5.8 Real-time WebSocket Streaming

Each incident analysis creates a WebSocket session identified by a `session_id` UUID. The frontend connects immediately after submitting the analysis request:

```
POST /api/v1/analyze/analyze-incident → returns session_id
WS  /api/v1/ws/{session_id}          → streams live status updates
```

The `ConnectionManager` singleton maintains a dict of `session_id → WebSocket` with per-session `asyncio.Lock` objects to prevent concurrent send races. Each agent sends status updates via the `ws_callback` async function injected into the `AgentState`.

**Message envelope format:**
```json
{
  "type": "status" | "complete" | "error",
  "step": "validation" | "classification" | "retrieval" | "mitigation" | "escalation" | "explanation" | "judge" | "complete" | "error",
  "message": "Human-readable status string",
  "data": {}
}
```

The frontend renders an animated agent timeline showing each step as it completes, giving analysts live feedback on analysis progress.

### 5.9 In-app Memory System

The `MemoryService` manages three types of per-user memory:

| Type | Description | Example |
|------|-------------|---------|
| `episodic` | Records of specific past events | "Analysed brute force incident on 2026-05-14" |
| `semantic` | General factual knowledge about the environment | "Production database is at 10.0.0.50" |
| `procedural` | How-to knowledge derived from past actions | "Blocking port 22 at the edge firewall resolved a brute force campaign" |

Memory entries are stored in the `memory_entries` PostgreSQL table and embedded into the `cybersentinel_memory` Qdrant collection. The `semantic_search_memory` function embeds a query and searches for the most relevant past memory fragments scoped to the authenticated user. The `remember_mitigation` function automatically creates procedural memory entries when analysts submit feedback with `mitigation_worked=true/false`.

### 5.10 Redis Caching Strategy

Redis is used for two caching purposes:

**ML prediction cache:**
- Key: `cybersentinel:predict:{sha256[:24]}` where the hash is over the JSON-serialised feature dict (sorted keys).
- TTL: 1,800 seconds (30 minutes).
- Rationale: The same network flow features (e.g., dest_port=22, source_port=54321, protocol=TCP) appear repeatedly in log-correlation scenarios. Caching eliminates redundant CPU-bound model inference.

**General cache helpers:**
- `cache_get(key)` / `cache_set(key, value, ttl)` are module-level async helpers that JSON-serialise/deserialise values and degrade gracefully if Redis is unavailable (returns `None` on miss).

### 5.11 Guardrails and Safety

The `GuardrailsValidator` module (`backend/app/guardrails/validator.py`) provides multi-layer input and output protection:

**Input validation:**
- Incident text: 10–5,000 characters; must be a non-empty string.
- IP address: validated with Python `ipaddress.ip_address()` — both IPv4 and IPv6 supported.
- Prompt injection detection: 19 compiled regex patterns covering common injection phrases (`ignore all previous instructions`, `jailbreak`, `DAN`, `[INST]`, `<system>` tags, `<|im_start|>`, etc.).
- Severity normalisation: maps aliases (crit → Critical, med → Medium, informational → Low) to canonical labels.

**Output sanitisation:**
- Scans LLM output for accidental credential leakage.
- Redacts: OpenAI API keys (`sk-...`), Bearer tokens, AWS access key IDs (`AKIA...`), AWS secret keys, GitHub PATs, JWT tokens (`eyJ...`), PEM private key blocks, and key=value pairs matching `password=`, `token=`, `api_key=`.
- Logs a warning if redaction occurs but does not block the response.

**Judge-layer safety:**
- The JudgeAgent flags any response where `is_safe=false` (dangerous advice, explicit exploit instructions, harmful content).
- A flagged response triggers one retry of the mitigation + explainability cycle.
- If the retry still fails, `is_safe=false` is included in the response and the frontend displays an appropriate warning.

---

## 6. Database Schema

All tables use UUIDs as primary keys and UTC timestamps. The schema is managed by SQLAlchemy ORM with Alembic migrations.

### `incidents`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Auto-generated incident UUID |
| `user_id` | VARCHAR(255) | NOT NULL, INDEX | Clerk user ID of the submitting analyst |
| `timestamp` | TIMESTAMPTZ | NULLABLE | Original incident timestamp (from CSV or manual entry) |
| `source_ip` | VARCHAR(45) | NULLABLE | Source IP address (IPv4 or IPv6) |
| `dest_ip` | VARCHAR(45) | NULLABLE | Destination IP address |
| `protocol` | VARCHAR(32) | NULLABLE | Network protocol (TCP, UDP, SSH, etc.) |
| `attack_type` | VARCHAR(128) | NULLABLE, INDEX | AI-classified or manually specified attack type |
| `severity` | ENUM | NULLABLE, INDEX | low / medium / high / critical |
| `label` | VARCHAR(128) | NULLABLE | Human-readable title or label |
| `raw_text` | TEXT | NULLABLE | Full incident description |
| `embedding_id` | VARCHAR(64) | NULLABLE | UUID of the corresponding Qdrant point |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Record creation timestamp |

### `conversations`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Conversation UUID (doubles as session_id) |
| `user_id` | VARCHAR(255) | NOT NULL, INDEX | Owning analyst's Clerk user ID |
| `title` | VARCHAR(512) | NULLABLE | Auto-generated from threat class (e.g. "Incident Analysis — Brute Force") |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now(), onupdate | Updated on every new message |

### `messages`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Message UUID |
| `conversation_id` | UUID | FK → conversations.id ON DELETE CASCADE, INDEX | Parent conversation |
| `role` | ENUM | NOT NULL | user / assistant / system |
| `content` | TEXT | NOT NULL | Message text (user: incident description; assistant: JSON analysis) |
| `metadata` | JSON | NULLABLE | Flexible payload: token counts, tool calls, citations, threat_class, escalation_level, judge_score |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### `analyst_feedback`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Feedback UUID |
| `incident_id` | UUID | FK → incidents.id ON DELETE SET NULL, NULLABLE, INDEX | Incident being rated |
| `conversation_id` | UUID | FK → conversations.id ON DELETE SET NULL, NULLABLE, INDEX | Associated conversation |
| `user_id` | VARCHAR(255) | NOT NULL, INDEX | Submitting analyst |
| `rating` | INTEGER | NULLABLE | 1 (very poor) to 5 (excellent) |
| `comment` | TEXT | NULLABLE | Free-text analyst notes |
| `mitigation_worked` | BOOLEAN | NULLABLE | Whether the suggested mitigation was effective |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### `memory_entries`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Memory entry UUID |
| `user_id` | VARCHAR(255) | NOT NULL, INDEX | Owning analyst |
| `content` | TEXT | NOT NULL | Memory text (plain language) |
| `embedding_id` | VARCHAR(64) | NULLABLE | Qdrant point UUID for semantic search |
| `memory_type` | VARCHAR(64) | NULLABLE, INDEX | episodic / semantic / procedural |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

---

## 7. API Reference

All endpoints are prefixed with `/api/v1`. Authentication is required unless noted. Bearer JWT must be a valid Clerk token.

### Ingest

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/ingest/upload-csv` | Admin | Upload a CSV file and batch-ingest incidents into Postgres, Qdrant, and Neo4j. Multipart form upload. |
| `POST` | `/ingest/build-index` | Admin | Re-embed all incidents from Postgres into Qdrant. Processes in batches of 50. |

### Analyze

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/analyze/analyze-incident` | Any role | Run the full 8-agent LangGraph workflow. Returns `AnalyzeIncidentResponse`. |

**Request body (`AnalyzeIncidentRequest`):**
```json
{
  "incident_text": "string (required, 10–5000 chars)",
  "severity": "low|medium|high|critical (optional)",
  "source_ip": "string IPv4/IPv6 (optional)",
  "dest_ip": "string IPv4/IPv6 (optional)",
  "protocol": "string (optional)",
  "session_id": "UUID string (optional, new UUID generated if omitted)"
}
```

**Response body (`AnalyzeIncidentResponse`):**
```json
{
  "threat_class": "brute_force",
  "severity_score": 0.93,
  "similar_incidents": [
    {
      "id": "uuid",
      "score": 0.87,
      "attack_type": "brute_force",
      "severity": "high",
      "summary": "Multiple SSH login failures from 10.0.0.1..."
    }
  ],
  "mitigation": {
    "containment": ["Block source IP at perimeter firewall..."],
    "eradication": ["Audit authentication logs..."],
    "recovery": ["Re-enable accounts after password reset..."],
    "prevention": ["Enforce MFA on all accounts..."]
  },
  "escalation_level": "L3",
  "explanation": "The incident was classified as a brute_force attack...",
  "judge_score": 0.9,
  "graph_data": {},
  "session_id": "uuid"
}
```

### Search

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/search/similar` | Any role | Hybrid similarity search. Body: `{query, attack_type?, severity?, protocol?, limit?}`. Returns ranked incidents. |
| `GET` | `/search/incident/{incident_id}` | Any role | Neo4j subgraph for a specific incident (nodes + edges for ReactFlow). |

### ML Prediction

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/predict-threat` | None | Predict threat from network flow features. Body: `{source_port, dest_port, protocol, packet_length, flow_duration, packet_rate}`. |
| `GET` | `/predict-threat/model-info` | None | Return model metadata: accuracy, training date, feature names, classes. |
| `GET` | `/predict-threat/feature-importance` | None | Return global feature importance list sorted descending. |

### Feedback

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/feedback/` | Any role | Submit analyst feedback. Body: `{incident_id, rating (1–5), comment?, mitigation_worked}`. |
| `GET` | `/feedback/stats` | Manager/Admin | Aggregated feedback statistics by attack type. |

### Memory

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/memory/conversations` | Any role | List the authenticated user's conversations (most recent first). |
| `GET` | `/memory/conversations/{id}/messages` | Any role | Get all messages in a conversation. |
| `POST` | `/memory/entries` | Any role | Store a long-term memory entry. Body: `{content, memory_type?}`. |
| `GET` | `/memory/search` | Any role | Semantic search over user's memory entries. Query param: `q`. |

### WebSocket

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `WS` | `/ws/{session_id}` | JWT in query param | Real-time agent status updates for the given session. |

### System

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | None | Liveness probe returning `{status, app, version, debug}`. |

---

## 8. Security Considerations

### Authentication and Authorisation
- All API endpoints (except `/health` and ML prediction) require a valid Clerk JWT.
- The JWT is validated against the Clerk JWKS endpoint on every request; short-lived tokens (default 60 seconds) limit replay attack windows.
- Role-based access control (analyst / manager / admin) is enforced at the route level via the `get_current_user` dependency.
- Admin-only routes (CSV upload, index build) return HTTP 403 to non-admin users.

### Input Validation and Prompt Injection
- Every incident text input passes through 19 prompt-injection regex patterns before reaching any LLM call.
- IP addresses are validated using Python's `ipaddress` module.
- Text length is bounded (10–5,000 characters) to prevent oversized context attacks.
- All validation failures return HTTP 422 with a descriptive error and do not consume LLM tokens.

### Output Sanitisation
- LLM outputs are scanned for credential patterns (API keys, JWTs, AWS credentials, private keys) before being included in API responses.
- Matched patterns are replaced with `[REDACTED_*]` placeholders.

### LLM Safety (Judge Layer)
- The JudgeAgent evaluates every generated response for safety violations (dangerous advice, explicit exploit instructions, harmful content).
- Unsafe responses trigger one regeneration attempt. If regeneration fails safety, the response is flagged in the output for analyst review.

### Transport Security
- All production traffic uses HTTPS/WSS (TLS termination at the load balancer or reverse proxy).
- CORS origins are restricted in production to `cybersentinel.ai` and `app.cybersentinel.ai`. The wildcard origin is only permitted when `DEBUG=true`.
- WebSocket sessions are keyed by UUID session IDs; the JWT is validated on connection establishment.

### Secret Management
- All secrets (OpenAI API key, Clerk keys, database passwords, Neo4j credentials) are loaded from environment variables via pydantic-settings. No secrets are committed to version control.
- The `.env.example` file contains placeholder values for all required variables.

### Dependency Security
- Backend dependencies are pinned in `requirements.txt` with minimum version constraints.
- The `python-jose[cryptography]` library handles JWT signature verification with industry-standard algorithms.

---

## 9. Performance and Scalability

### Async Architecture
FastAPI's ASGI runtime handles all I/O-bound work (database queries, HTTP calls to OpenAI, Qdrant, Neo4j) without blocking the event loop. Concurrent requests share a single event loop and do not require thread pools.

### LangGraph Workflow Concurrency
The compiled LangGraph workflow is a singleton compiled once at startup. LangGraph's state isolation model allows multiple concurrent `ainvoke` calls against the same compiled graph, each with its own `AgentState` dict.

### Redis Caching
ML predictions are cached for 30 minutes. This reduces OpenAI embedding API calls and eliminates repeated model inference for common attack patterns.

### Database Connection Pooling
SQLAlchemy's async engine uses connection pooling (default pool size 5, max overflow 10). The Qdrant and Neo4j clients maintain their own connection pools. Redis uses a single persistent connection.

### Batch Embedding
The ingest pipeline embeds documents in batches of 50 to respect OpenAI rate limits while maximising throughput.

### Horizontal Scaling
The FastAPI application is stateless (session state is in Redis; persistence is in the databases). Multiple instances can run behind a load balancer. WebSocket sessions require sticky routing to the same instance or a shared Redis pub/sub backend.

### Vector Search Performance
Qdrant's HNSW index provides sub-millisecond approximate nearest-neighbour search at millions of vectors. Metadata filtering is pushed into the index layer, avoiding post-filtering overhead.

---

## 10. Future Enhancements

1. **Streaming LLM responses** — Use OpenAI streaming (`stream=True`) to push token-by-token mitigation and explanation text through the WebSocket, further reducing perceived latency.
2. **Fine-tuned classification model** — Fine-tune a smaller model (e.g., GPT-4o-mini) on the historical incident knowledge base to improve threat classification accuracy on organisation-specific incident patterns.
3. **Automated SOAR integration** — Connect the escalation output to SOAR platforms (Splunk SOAR, Palo Alto XSOAR) to automatically open tickets, page on-call analysts, and trigger containment playbooks.
4. **Multi-modal input** — Accept network packet captures (PCAP) and SIEM export files in addition to free-text descriptions. Parse them into structured incident representations before analysis.
5. **Federated knowledge graph** — Merge the organisation's Neo4j graph with MITRE ATT&CK STIX data and threat intelligence feeds (AlienVault OTX, MISP) to enrich mitigation recommendations.
6. **Analyst feedback RLHF loop** — Use analyst ratings and `mitigation_worked` signals to fine-tune the mitigation generation model via DPO or RLHF, closing the feedback loop automatically.
7. **Anomaly-based ML model** — Supplement the RandomForest classifier with an autoencoder-based anomaly detection model for zero-day threat identification.
8. **Multi-tenancy** — Add organisation-level data isolation with row-level security in PostgreSQL and per-organisation Qdrant collections.
9. **Audit logging** — Persist a tamper-evident audit log of all analyst actions, API calls, and AI decisions to an append-only store for compliance (SOC 2, ISO 27001).
10. **Graph algorithm enrichment** — Run PageRank and community detection (Neo4j GDS) over the incident graph to identify pivotal infrastructure nodes and coordinated attack campaigns automatically.

---

## 11. Sample Queries and Responses

### Sample 1: SSH Brute Force

**Query:**
```
Multiple failed SSH login attempts from 192.168.1.25 targeting 10.0.0.5 over TCP port 22.
Over 500 failed attempts in the last 10 minutes. Severity high.
```

**Expected output summary:**
- `threat_class`: `brute_force`
- `severity_score`: 0.94
- `escalation_level`: `L3` (high severity + high confidence)
- `mitigation.containment[0]`: "Block the offending source IP at the perimeter firewall immediately."
- `judge_score`: ~0.90
- `similar_incidents`: 3–7 historical SSH brute force records

---

### Sample 2: Suspected Malware C2 Communication

**Query:**
```
Workstation WIN-001 is making repeated outbound connections to 185.220.101.45:4444 over TCP.
Process: powershell.exe. Parent: explorer.exe. Packet rate unusually high.
```

**Expected output summary:**
- `threat_class`: `malware`
- `escalation_level`: `SOC_Manager` (critical class, high confidence)
- `mitigation.containment[0]`: "Immediately isolate infected hosts from the network (VLAN quarantine or physical disconnect)."

---

### Sample 3: DDoS Volumetric Attack

**Query:**
```
Our public API at 203.0.113.50 is receiving 150,000 requests per second from distributed
IP ranges. Application response time exceeds 30 seconds. CDN rate limiting is ineffective.
```

**Expected output summary:**
- `threat_class`: `ddos`
- `escalation_level`: `SOC_Manager`
- `mitigation.containment`: Enable upstream DDoS scrubbing service, activate null-route for aggressive source ranges.
- `mitigation.prevention`: Subscribe to dedicated DDoS mitigation service, implement anycast network diffusion.

---

### Sample 4: Phishing Campaign

**Query:**
```
Email gateway flagged 47 emails with subject "Your account has been compromised - immediate action required"
containing links to hxxp://secure-login-verify[.]xyz. Three users clicked the link.
```

**Expected output summary:**
- `threat_class`: `phishing`
- `escalation_level`: `L3`
- `mitigation.eradication`: Delete phishing emails from all mailboxes using admin purge; block phishing domain at email gateway.
- `explanation`: Explains the social engineering vector, credential harvesting risk, and why three confirmed clicks elevate the severity.

---

### Sample 5: Network Intrusion (Lateral Movement)

**Query:**
```
IDS alert: internal host 10.0.10.55 scanning subnet 10.0.20.0/24 on ports 445, 3389, 22.
Originates from a finance department workstation. No authorized scan scheduled.
```

**Expected output summary:**
- `threat_class`: `network_intrusion`
- `escalation_level`: `L3` (high severity internal scan)
- `mitigation.containment`: Block the scanning host's outbound connections; isolate from the corporate network segment.
- `mitigation.prevention`: Implement Zero Trust Network Access (ZTNA) architecture; deploy next-generation IDS/IPS.

---

## Feature Set v2 — Advanced Differentiators

**Version:** 2.0.0  
**Date:** 2026-06-09  
**Status:** General Availability

This section documents the twenty advanced features introduced in CyberSentinel AI v2. Each feature is described with the problem it solves, its implementation approach, API contract, and UI representation. These capabilities collectively differentiate CyberSentinel AI from first-generation AI-assisted triage tools by delivering a complete, production-hardened incident response lifecycle.

---

### Feature 1 — MITRE ATT&CK Mapping

**Problem it solves:** Threat classifications expressed as internal labels (e.g., `brute_force`, `malware`) lack the standardised vocabulary required for cross-team communication, regulatory reporting, and threat intelligence sharing. Analysts waste time manually cross-referencing the ATT&CK framework.

**Implementation approach:** A dedicated MITRE service maintains a curated local knowledge base of ATT&CK tactics, techniques, and sub-techniques keyed by attack type. At analysis time, the service extends this base lookup with a Neo4j graph query that retrieves MITRE-mapped technique nodes for incidents sharing the same `AttackType`. Confidence scores are derived from the hybrid scoring formula: `(mitre_confidence × 0.45) + (graph_rag_similarity × 0.35) + (keyword_match × 0.20)`.

**API contract:**
```
POST /api/v1/mitre/map
Body:  { "incident_id": "uuid", "threat_class": "brute_force" }
Response: {
  "tactic": "Credential Access",
  "technique_id": "T1110",
  "technique_name": "Brute Force",
  "sub_technique_id": "T1110.001",
  "sub_technique_name": "Password Guessing",
  "confidence": 0.91,
  "mitre_url": "https://attack.mitre.org/techniques/T1110/"
}
```

**UI description:** The MITRE ATT&CK tab in the war room renders a colour-coded ATT&CK matrix heatmap highlighting the detected tactic column and technique cell. A detail card shows the technique ID, full name, description, and a direct link to the ATT&CK knowledge base.

---

### Feature 2 — AI Incident War Room

**Problem it solves:** Incident investigation is fragmented across SIEM dashboards, ticketing systems, chat tools, and standalone analysis tools. There is no single workspace where analysts can view all evidence, run AI analysis, and coordinate in real time.

**Implementation approach:** The war room is a WebSocket-driven React workspace mounted at `/war-room/{incident_id}`. A `ConnectionManager` maintains per-incident broadcast channels; multiple analysts can connect to the same war room simultaneously and receive identical live updates. The room persists its state in the `incidents` and `conversations` tables, allowing analysts to re-enter a war room after disconnection and see the full history.

**API contract:**
```
WS /api/v1/ws/war-room/{incident_id}
Emitted events: { type: "status"|"complete"|"error", step: string, message: string, data: {} }
```

**UI description:** Tabbed layout with six panels: (1) Evidence — raw incident text, network metadata, analyst notes; (2) MITRE — ATT&CK mapping and heatmap; (3) Risk Score — gauge chart with factor breakdown; (4) Threat Intel — enrichment results for all IPs, domains, and hashes; (5) Agent Timeline — animated step-by-step workflow progress; (6) Analyst Chat — free-text collaboration log with timestamp.

---

### Feature 3 — Human-in-the-Loop Approval

**Problem it solves:** Fully automated AI response recommendations applied without human review create liability and compliance risk. SOC managers require a structured review gate before any mitigation is actioned.

**Implementation approach:** After the LangGraph workflow completes and the judge scorecard is produced, an `incident_approvals` record is created with `status = pending`. The approval service exposes dedicated endpoints for each action. All state transitions are persisted with the acting analyst's Clerk user ID, timestamp, and any notes or edits. The approval status drives the UI display — pending items surface in the analyst's task queue.

**API contract:**
```
POST /api/v1/approval/{incident_id}/approve    — Approve the AI recommendation
POST /api/v1/approval/{incident_id}/reject     — Reject with mandatory reason
POST /api/v1/approval/{incident_id}/edit       — Submit analyst-edited mitigation
POST /api/v1/approval/{incident_id}/escalate   — Escalate to next tier
POST /api/v1/approval/{incident_id}/regenerate — Request AI to regenerate analysis
GET  /api/v1/approval/{incident_id}            — Retrieve current approval state and history
```

**UI description:** An approval panel within the war room displays the judge scorecard alongside four action buttons. The reject and edit actions open modal dialogs requiring a written rationale. Escalation auto-updates the SLA tracker. All approval actions are reflected immediately in the audit log.

---

### Feature 4 — LLM-as-Judge Scorecard

**Problem it solves:** AI-generated incident analyses vary in quality; hallucinations and incomplete responses erode analyst trust. A quality gate is required before recommendations are surfaced to human reviewers.

**Implementation approach:** After the `AssembleFinal` agent produces the full response, the `JudgeAgent` invokes GPT-4.1-mini with a structured evaluation prompt requesting scores across five dimensions. Results are normalised to a 0–10 scale. A composite quality score is computed as `mean(correctness, completeness, relevance) − hallucination_penalty`. Responses scoring below 5.0 or flagged as unsafe trigger one retry of the mitigation and explainability agents. The scorecard is stored in `incident_approvals.judge_scorecard` for analyst review.

**API contract:**
```
POST /api/v1/judge/evaluate
Body: { "incident_id": "uuid", "analysis_output": {...} }
Response: {
  "correctness": 9.1, "safety": true, "completeness": 8.7,
  "relevance": 8.9, "hallucination_risk": "low",
  "composite_score": 8.9, "feedback": "Analysis is well-grounded..."
}
```

**UI description:** A scorecard card in the war room approval panel renders five labelled progress bars (one per dimension) with colour coding (green ≥ 8, amber 5–7.9, red < 5). A composite score badge displays the overall quality grade with a natural-language summary from the judge's feedback field.

---

### Feature 5 — SOC Executive Dashboard

**Problem it solves:** SOC leadership needs business-level visibility into security operations performance — MTTR, SLA compliance, analyst workload, and attack trend data — without navigating raw incident lists.

**Implementation approach:** The executive dashboard aggregates pre-computed metrics from the `incidents`, `sla_trackers`, `incident_approvals`, and `analyst_feedback` tables. A dedicated backend endpoint returns a structured metrics object that the frontend renders as charts. Metrics are computed on-demand with Redis caching (5-minute TTL) to keep the dashboard responsive at scale.

**API contract:**
```
GET /api/v1/dashboard/executive-metrics
Response: {
  "mttr_minutes": 18.4,
  "sla_breach_rate": 0.07,
  "open_incidents": 34,
  "critical_unreviewed": 5,
  "attack_type_distribution": { "brute_force": 42, "malware": 28, ... },
  "incidents_by_severity": { "critical": 8, "high": 26, ... },
  "analyst_workload": [ { "analyst_id": "...", "open_count": 12 }, ... ],
  "weekly_trend": [ { "date": "2026-06-02", "count": 47 }, ... ]
}
```

**UI description:** A full-page dashboard with six chart panels: (1) MTTR trend line chart; (2) SLA breach rate gauge; (3) attack type distribution donut chart; (4) incidents by severity stacked bar; (5) analyst workload heat map; (6) weekly incident volume trend. All panels support date range filtering and org-level scoping.

---

### Feature 6 — Auto Incident Report Generator

**Problem it solves:** Producing a structured, professional incident report after every significant event is time-consuming and inconsistently executed. Stakeholders require both a technical report and an executive summary.

**Implementation approach:** The report service assembles all structured analysis fields — incident description, MITRE mapping, risk score, threat intel enrichment, mitigation plan, escalation decision, judge scorecard, and approval decision — into a report template. Markdown reports are generated server-side using a template renderer. PDF reports are produced by passing the rendered Markdown through a headless PDF generator and returned as a binary response with a `Content-Disposition: attachment` header. Each report is stamped with a unique report ID and generation timestamp.

**API contract:**
```
POST /api/v1/report/{incident_id}/markdown  → text/markdown response
POST /api/v1/report/{incident_id}/pdf       → application/pdf binary response
```

**UI description:** A "Generate Report" button in the reports page and war room toolbar. Clicking it triggers report generation with a loading spinner, then opens a split-pane view: the left pane renders the Markdown preview with syntax highlighting; the right pane shows a PDF preview iframe. Download buttons for both formats appear in the toolbar.

---

### Feature 7 — MITRE + Graph RAG Combined Reasoning

**Problem it solves:** Neither MITRE ATT&CK lookups nor vector similarity alone provides sufficient context. MITRE provides technique-level structure; Graph RAG provides historical incident precedents. Combining them improves both coverage and precision.

**Implementation approach:** The hybrid reasoning layer runs MITRE mapping and Graph RAG retrieval concurrently. Results are fused using a weighted formula: `hybrid_score = (mitre_confidence × 0.45) + (graph_rag_similarity × 0.35) + (keyword_match × 0.20)`. The fused score is used to rank the context blocks injected into downstream LLM prompts. Neo4j stores MITRE technique nodes alongside incident nodes, enabling queries that traverse ATT&CK relationships directly in the graph.

**API contract:** Integrated into `POST /api/v1/analyze/analyze-incident` response as `mitre_graph_context` and `hybrid_score` fields.

**UI description:** The Evidence Panel in the war room displays a "Combined Reasoning" section listing the top-ranked context blocks with their hybrid scores, source labels (MITRE / Graph / Keyword), and `[REF-N]` citation markers.

---

### Feature 8 — Threat Intelligence Enrichment

**Problem it solves:** Raw incident data (IP addresses, domains, file hashes) requires enrichment from external threat intelligence sources before analysts can assess the true threat level. Manual lookups across multiple tools are slow and inconsistent.

**Implementation approach:** The threat intelligence service accepts IP addresses, domains, and SHA-256 hashes and queries reputation APIs in parallel. Results are normalised into a standard schema: `indicator_type`, `verdict` (malicious / suspicious / clean), `confidence`, `tags`, and `source`. Enrichment results are cached in Redis (1-hour TTL per indicator) to avoid redundant external calls.

**API contract:**
```
POST /api/v1/threat-intel/enrich
Body: { "indicators": [ { "type": "ip", "value": "185.220.101.45" }, ... ] }
Response: {
  "results": [
    { "indicator": "185.220.101.45", "type": "ip", "verdict": "malicious",
      "confidence": 0.94, "tags": ["tor-exit-node", "c2"], "source": "..." }
  ]
}
```

**UI description:** The Threat Intel tab in the war room renders a table of all extracted indicators with colour-coded verdict badges (red: malicious, amber: suspicious, green: clean), confidence bars, and expandable tag lists. Indicators are automatically extracted from the incident text and network metadata fields.

---

### Feature 9 — Risk Scoring Engine

**Problem it solves:** Incident severity labels (high, critical) are subjective and inconsistently applied. Security teams need an objective, explainable numerical risk score to prioritise response effort and communicate risk to stakeholders.

**Implementation approach:** The risk scoring engine computes a composite 0–100 score from three independently assessed dimensions: impact (how damaging is the incident?), likelihood (how confident is the threat assessment?), and asset criticality (how important are the affected systems?). Each dimension is scored 0–100 using a weighted sub-formula. The final composite formula is `impact × 0.40 + likelihood × 0.35 + asset_criticality × 0.25`. The engine returns both the scalar score and a complete factor breakdown.

**API contract:**
```
POST /api/v1/risk/score
Body: { "incident_id": "uuid", "attack_type": "...", "severity": "high",
        "affected_assets": ["10.0.0.5"], "historical_count": 12 }
Response: { "risk_score": 87, "impact": 91, "likelihood": 88,
            "asset_criticality": 79, "breakdown": { ... } }
```

**UI description:** A semicircular gauge chart displaying the 0–100 score with colour zones (green 0–39, amber 40–69, red 70–100). Below the gauge, a factor breakdown table lists each dimension with its sub-score and a one-sentence rationale.

---

### Feature 10 — Continuous Feedback Learning

**Problem it solves:** AI recommendations that are not reinforced by analyst feedback degrade in relevance over time. A structured feedback loop is essential for continuous model improvement and organisational knowledge retention.

**Implementation approach:** The feedback service captures analyst ratings (1–5), mitigation effectiveness signals (boolean), and free-text comments after each incident. Ratings are aggregated into per-attack-type statistics returned by the feedback stats endpoint. The `MemoryService.remember_mitigation` function automatically converts `mitigation_worked=true` signals into procedural memory entries scoped to the relevant attack type, which are retrieved as context in future similar incidents.

**API contract:**
```
POST /api/v1/feedback/         — Submit feedback for an incident
GET  /api/v1/feedback/stats    — Aggregated stats by attack type (manager/admin only)
```

**UI description:** A feedback panel at the bottom of the incident analysis card with a 5-star rating widget, a mitigation effectiveness toggle, and an optional comment text area. The `/feedback` page provides a statistics view with average ratings, effectiveness rates, and volume by attack type displayed as bar charts.

---

### Feature 11 — Policy-Aware Guardrails

**Problem it solves:** Generic LLM prompt-injection protection is insufficient for a cybersecurity platform where the input space intentionally includes malicious content. Additionally, the platform must not provide offensive cyber capabilities to analysts, regardless of how requests are framed.

**Implementation approach:** The `GuardrailsValidator` extends base prompt-injection detection (19 compiled regex patterns) with a dedicated offensive cyber action blocklist. This blocklist detects and rejects requests containing instructions to write exploits, generate malware, bypass authentication systems, or attack external infrastructure. Policy rules are configurable per organisation via the `guardrails/validate` endpoint and stored in the org's memory scope.

**API contract:**
```
POST /api/v1/guardrails/validate
Body: { "text": "string", "context": "incident_analysis" }
Response: { "is_valid": true/false, "violations": ["..."], "sanitized_text": "..." }
```

**UI description:** Validation feedback is surfaced inline in the incident submission form. Detected violations display as labelled warning banners below the text input field, specifying the violation type and suggesting compliant reformulations.

---

### Feature 12 — Advanced Memory Scopes

**Problem it solves:** A single per-user memory scope is insufficient for enterprise deployments where memory should persist at the incident level (case-specific context), the organisation level (shared institutional knowledge), and the mitigation level (what has worked before).

**Implementation approach:** The `MemoryService` implements five independent scopes: `user` (personal episodic memory), `incident` (case-specific context), `org` (organisation-wide shared knowledge), `mitigation` (playbook effectiveness history), and `false_positive` (known benign patterns registry). Each scope is stored with an `owner_id` (user ID or org ID) in `memory_entries` and indexed in a dedicated Qdrant collection with payload filters for scope-level isolation.

**API contract:**
```
GET  /api/v1/memory/user          — Retrieve user-scoped memory entries
GET  /api/v1/memory/org           — Retrieve org-scoped memory entries
POST /api/v1/memory/save          — Save a memory entry with specified scope
POST /api/v1/memory/search        — Semantic search across specified scopes
```

**UI description:** The `/memory` page provides a tabbed browser for each memory scope with a semantic search bar, entry cards showing content, type, and creation date, and buttons to manually add or delete entries.

---

### Feature 13 — Realtime WebSocket Agent Progress

**Problem it solves:** A single "loading" spinner during multi-agent AI analysis provides no insight into what the system is doing, eroding analyst confidence. Analysts need visibility into each processing step.

**Implementation approach:** Each LangGraph agent emits a typed WebSocket event upon completion: `{type, step, message, data, elapsed_ms, progress_pct}`. The `ConnectionManager` singleton maintains per-incident WebSocket broadcast groups, allowing multiple analysts connected to the same war room to receive identical progress events. Agent names, descriptions, and expected durations are defined in a registry so the frontend can render predictive progress bars.

**API contract:**
```
WS /api/v1/ws/war-room/{incident_id}
Events: { "type": "status", "step": "classification", "message": "Threat classified as brute_force (91%)",
          "data": { "threat_class": "brute_force", "confidence": 0.91 },
          "elapsed_ms": 1240, "progress_pct": 28 }
```

**UI description:** An animated vertical timeline in the war room's Agent Timeline tab. Each agent node displays its name, a status icon (pending / running / complete / error), elapsed time, and key output data. Running nodes display a pulsing animation. Completed nodes show a checkmark with the elapsed time.

---

### Feature 14 — Playbook Generator

**Problem it solves:** Mitigation plans generated per-incident are not reusable. SOC teams need standardised, organisation-specific playbooks that can be assigned to incidents, reviewed, and executed step-by-step.

**Implementation approach:** The playbook generator invokes GPT-4.1-mini with a structured prompt combining the incident's attack type, MITRE mapping, risk score, threat intel enrichment, and relevant procedural memory entries. The output is a structured playbook with named phases, assigned roles, estimated durations, and checklists. Playbooks are persisted and linked to the incident. Analysts can customise and version playbooks within the platform.

**API contract:**
```
POST /api/v1/playbook/generate
Body: { "incident_id": "uuid", "customization_notes": "..." }
Response: { "playbook_id": "uuid", "title": "...", "phases": [ { "name": "Containment",
            "steps": [...], "assigned_role": "analyst", "estimated_minutes": 15 } ], ... }
```

**UI description:** A "Generate Playbook" button in the war room toolbar opens a full-page playbook view with collapsible phase cards. Each card displays a checklist of steps with role assignments, estimated durations, and completion checkboxes. Playbooks can be exported as PDF or linked to ticketing systems.

---

### Feature 15 — Simulation Mode

**Problem it solves:** Validating platform behaviour against realistic attack scenarios without affecting production data requires a dedicated testing environment. Demos and training exercises need reproducible, realistic scenarios.

**Implementation approach:** The simulation service maintains a catalogue of predefined attack scenarios (e.g., Ransomware Infection, Credential Stuffing, Supply Chain Compromise). Each scenario has a fixed incident description, severity, network metadata, and expected analysis outputs. Running a scenario invokes the full LangGraph pipeline in a sandboxed context — all results are stored under a `simulation` tag and do not affect production metrics or audit logs. Scenarios can also be used for regression testing after model or pipeline updates.

**API contract:**
```
GET  /api/v1/simulation/scenarios              — List all available scenarios
POST /api/v1/simulation/run/{scenario_id}      — Execute a scenario
Response: { "run_id": "uuid", "scenario": {...}, "analysis": {...}, "war_room_url": "/war-room/..." }
```

**UI description:** The `/simulation` page displays a grid of scenario cards, each with a title, threat type badge, severity indicator, and a brief description. Clicking a card opens a pre-filled incident form with a "Run Simulation" button. Results stream into the war room in real time, indistinguishable from a live incident analysis.

---

### Feature 16 — Explainability Panel

**Problem it solves:** AI-generated recommendations are often treated as black-box outputs, reducing analyst trust and hindering skill development. Analysts need to understand why the AI reached each conclusion.

**Implementation approach:** The `ExplainabilityAgent` produces a multi-section explanation covering: (1) classification rationale — which features and retrieved precedents drove the threat class decision; (2) MITRE mapping justification — which observed behaviours map to which ATT&CK technique; (3) risk score breakdown — factor-level justification for each component score; (4) mitigation reasoning — why each phase is recommended given the specific incident context. All `[REF-N]` citations in the explanation are linked to the corresponding retrieved incidents.

**API contract:** Integrated into `POST /api/v1/analyze/analyze-incident` response as the `explanation` field, containing the full multi-section natural-language explanation with inline `[REF-N]` citation markers.

**UI description:** A collapsible "Explainability" card in the war room with four expandable sections (Classification, MITRE, Risk, Mitigation). Clicking a `[REF-N]` citation opens a side drawer displaying the full retrieved incident record. A "Show Reasoning Trace" toggle reveals the agent-level decision chain.

---

### Feature 17 — Escalation SLA Tracker

**Problem it solves:** Incidents assigned to analysts without time-bound commitments are frequently deprioritised. SLA breaches are only discovered retrospectively, after damage is done.

**Implementation approach:** The SLA service assigns a deadline to every incident based on the escalation level and organisational SLA policy (L1: 4h, L2: 2h, L3: 1h, SOC_Manager: 30m). A background job running every 5 minutes evaluates all open `sla_trackers` records, marks breached SLAs, and emits WebSocket breach-alert events to the assigned analyst. SLA compliance metrics are aggregated in the executive dashboard as a KPI.

**API contract:**
```
POST /api/v1/sla/assign       — Assign SLA to an incident
GET  /api/v1/sla/{incident_id} — Get current SLA state and breach status
```

**UI description:** A countdown timer badge on each war room header showing time remaining before SLA breach. Breached SLAs display a red pulsing badge. The executive dashboard "SLA Breach Rate" KPI panel charts breach rates over time by escalation level.

---

### Feature 18 — Secure Audit Logs

**Problem it solves:** Enterprise security teams require a complete, tamper-evident record of all AI decisions, analyst actions, and system events for regulatory compliance (SOC 2, ISO 27001, GDPR), incident post-mortems, and insider threat investigation.

**Implementation approach:** All significant platform events — incident submission, analysis completion, approval decisions, report downloads, feedback submissions, memory modifications, and administrative actions — are appended to the `audit_logs` table with the actor's identity, timestamp, resource UUID, and event-specific payload. The table uses an append-only constraint (no UPDATE or DELETE permissions granted to the application service account). The admin UI provides a filtered, paginated view of the audit log.

**API contract:**
```
GET /api/v1/audit-logs/
Query params: ?actor_id=...&event_type=...&from_date=...&to_date=...&limit=100
Response: { "logs": [ { "id": "uuid", "actor_id": "...", "event_type": "...",
            "resource_id": "...", "payload": {...}, "created_at": "..." } ], "total": 847 }
```

**UI description:** The `/audit-logs` page (admin-only) renders a searchable, filterable log table with columns for timestamp, actor, event type, resource ID, and a "View Details" button that opens the full event payload in a JSON viewer modal.

---

### Feature 19 — Multi-Tenant SaaS Support

**Problem it solves:** Enterprise customers require complete data isolation between organisations. A shared-database multi-tenant architecture without proper isolation creates data leakage risk and violates enterprise security policies.

**Implementation approach:** Multi-tenancy is implemented via Clerk Organisations. Each API request includes an `org_id` extracted from the Clerk JWT organisation claims. All database queries — incidents, memory, approvals, audit logs, feedback, SLA records — are filtered by `org_id` at the application layer. Qdrant searches include an `org_id` payload filter. Neo4j queries include organisation identity in MERGE conditions. Organisation administrators can configure org-level SLA policies, guardrail rules, and memory scope settings through the admin interface.

**API contract:** `org_id` is not a request parameter — it is extracted from the authenticated JWT on every request. Organisation-level settings are managed through the Clerk organisation API and the platform's admin endpoints.

**UI description:** After sign-in, analysts operating in multiple organisations can switch organisation context via the Clerk organisation switcher in the top navigation bar. All data, dashboards, and settings update immediately to reflect the selected organisation's scope.

---

### Feature 20 — MCP Tool Marketplace

**Problem it solves:** The MCP server's capabilities are not discoverable from within the platform. Analysts and administrators have no in-product interface to browse available tools, test them interactively, or understand their capabilities and usage.

**Implementation approach:** The MCP marketplace endpoint introspects the running MCP server to retrieve all registered tool schemas, descriptions, input parameters, and example invocations. The frontend renders this information as a searchable tool catalogue. Each tool card includes an inline test runner that allows analysts to invoke the tool with custom parameters and view the live response — without leaving the platform.

**API contract:**
```
GET  /api/v1/mcp/tools                    — List all available MCP tools with schemas
POST /api/v1/mcp/tools/{tool_name}/test   — Invoke a tool with provided parameters
```

**UI description:** The `/mcp-tools` page displays a grid of tool cards, each showing the tool name, description, parameter schema table, and an example invocation. A "Test Tool" button expands an inline form populated from the schema, with a "Run" button that fires the request and renders the JSON response in a syntax-highlighted panel. A connection status indicator shows whether the MCP server is reachable.

---

## Final Premium Feature Set

**Version:** 3.0.0  
**Date:** 2026-06-10  
**Status:** General Availability

Six enterprise-grade features built on top of the v2 platform. Every feature follows the same production standards as v2: async FastAPI routes, SQLAlchemy 2.0 ORM models, Clerk JWT authentication, `org_id` multi-tenant isolation, `audit_log_service.log_event()` on every endpoint, WebSocket event streaming via `ws_callback`, and mock fallbacks for operation without API keys.

---

### Feature 21 — Agent Self-Reflection Engine

**Problem it solves:** The LLM-as-Judge provides a quality score but does not automatically trigger remediation when that score is low. A reflection loop that critiques the analysis and produces an improved version closes this gap without requiring analyst intervention.

**Implementation approach:** After the JudgeAgent assigns a score, a `should_reflect` conditional edge evaluates `judge_score < _REFLECTION_SCORE_THRESHOLD` (default 7.5). When triggered, the `SelfReflectionAgent` makes two sequential LLM calls: the first detects weaknesses (missing evidence, low-confidence areas, incomplete reasoning), and the second produces an improved analysis with the detected gaps injected as additional context. A `_build_comparison()` helper generates a structured before/after delta. Results are persisted in `self_reflections`.

**API contract:**
```
POST /api/v1/reflection/analyze
Body: { "incident_text": "...", "initial_analysis": {...}, "judge_score": 6.2,
        "incident_id": "uuid?" }
Response: {
  "reflection_triggered": true,
  "weaknesses_detected": ["incomplete containment steps", "missing C2 analysis"],
  "missing_evidence": ["lateral movement indicators"],
  "improved_analysis": {...},
  "before_after_comparison": { "added": [...], "changed": [...], "removed": [...] },
  "final_confidence": 8.4
}
```

**UI description:** A "Self-Reflection" tab in the war room. Displays the reflection trigger decision (triggered / skipped), final confidence score, an expandable weakness list, missing evidence tags, and a two-column before/after comparison card with colour-coded change indicators. A "Run Reflection" button triggers the analysis manually.

---

### Feature 22 — Attack Campaign Detection

**Problem it solves:** Individual incident analysis misses coordinated multi-incident attacks that span time windows and IP ranges. SOC teams need automated clustering to detect campaigns before adversaries complete their objectives.

**Implementation approach:** The `CampaignDetectionService.detect_campaigns()` function performs O(n²) pairwise incident scoring using five weighted similarity signals: IP /24 subnet overlap (0.25, via Python `ipaddress` module), attack type match (0.25), MITRE technique overlap (0.25), protocol match (0.10), and severity proximity (0.15). Pairs scoring ≥ 0.6 are merged into clusters. Each cluster is profiled by GPT (or a heuristic fallback) to generate a campaign name, attack narrative, and threat actor profile. Results are stored in the `campaigns` + `campaign_incidents` tables.

**API contract:**
```
POST /api/v1/campaigns/detect
Body: { "incidents": [ { "id": "...", "source_ip": "...", "attack_type": "...",
         "severity": "...", "mitre_technique": "?" } ], "time_window_hours": 24 }
Response: { "campaigns_detected": 2, "campaigns": [ {
  "campaign_id": "uuid",
  "campaign_name": "Credential Harvesting Campaign",
  "campaign_confidence": 0.91,
  "related_incidents": ["INC-102", "INC-118"],
  "shared_indicators": ["subnet 45.33.x.x", "T1110"],
  "attack_narrative": "...",
  "threat_actor_profile": "..."
} ] }

GET /api/v1/campaigns          → paginated campaign list for org
GET /api/v1/campaigns/{id}     → full campaign detail with timeline and response
```

**UI description:** The `/campaigns` page shows a stats row (active / total / avg confidence), a search bar, and campaign cards with confidence and status badges. Clicking a card opens the `/campaigns/[campaignId]` detail page with four tabs: Overview (attack narrative, threat actor profile, related incidents, MITRE techniques, source IPs, targeted assets), Timeline (vertical event list), Indicators (shared IOCs + cluster statistics), and Response (recommended countermeasures).

---

### Feature 23 — Autonomous Investigation Mode

**Problem it solves:** Standard incident analysis requires the analyst to manually drive follow-up investigation steps (check IP reputation, query the graph, search similar incidents, etc.). Autonomous mode chains all these steps into a single pipeline, producing a complete investigation report without analyst orchestration.

**Implementation approach:** The `AutonomousInvestigationAgent` executes eight MCP tool functions in sequence, each recording its inputs, outputs, duration, and sequence number. A `_call_tool()` wrapper handles per-tool telemetry. The pipeline: (1) MITRE mapping, (2) IP reputation lookup, (3) graph relationship query, (4) similar incident search, (5) risk calculation, (6) mitigation recommendation, (7) guardrails check, (8) final report generation. All results are assembled into an `evidence_chain` and `findings` dict, then scored by the judge. Persisted in `autonomous_investigations` and `investigation_tool_calls`.

**API contract:**
```
POST /api/v1/investigation/autonomous
Body: { "incident_text": "...", "source_ip": "?", "severity": "?", "incident_id": "?" }
Response: {
  "investigation_id": "uuid",
  "tool_calls": [ { "tool": "map_to_mitre", "sequence": 1, "duration_ms": 340,
                    "output": { "technique_id": "T1110", ... } } ],
  "evidence_chain": { "mitre": {...}, "ip_reputation": {...}, ... },
  "findings": { "threat_level": "high", "confidence": 0.89, ... },
  "final_summary": "...",
  "recommended_actions": ["..."],
  "judge_score": 8.7,
  "total_tool_calls": 8,
  "duration_seconds": 12.4,
  "status": "completed"
}
```

**WebSocket events:** Each tool call emits `{ type: "tool_call", tool: "map_to_mitre", sequence: 1, status: "complete", duration_ms: 340 }` so the frontend can animate the tool pipeline in real time.

**UI description:** An "Auto Investigation" tab in the war room with a vertical animated tool call timeline (tool name, sequence badge, duration, status icon), a collapsible evidence chain panel, a findings summary card, and the final judge-scored report.

---

### Feature 24 — Multi-LLM Consensus Engine

**Problem it solves:** Single-model analysis introduces single-model bias. Adversarial or ambiguous incidents benefit from independent perspectives. Disagreements between models are themselves a signal of analytical uncertainty.

**Implementation approach:** The `ConsensusService` invokes three LLM analyzers concurrently: `_analyze_with_openai()` (GPT-4.1-mini, weight 0.45), `_analyze_with_claude()` (Claude Haiku via Anthropic SDK, weight 0.35), and `_analyze_with_llama()` (Llama 3 via Ollama, weight 0.20). The `_adjust_weights()` function redistributes weights proportionally when any model is unavailable. `_compute_consensus()` performs weighted majority voting for classification and weighted averaging for severity scores. The `agreement_score` is the weighted fraction of models aligned on the winning classification. Results are stored in `consensus_results` and `consensus_model_outputs`.

**API contract:**
```
POST /api/v1/consensus/analyze
Body: { "incident_text": "...", "incident_id": "?" }
Response: {
  "model_outputs": [
    { "model": "openai", "weight": 0.45, "classification": "brute_force",
      "severity": "high", "confidence": 0.91, "key_findings": [...] },
    { "model": "anthropic", "weight": 0.35, ... },
    { "model": "local", "weight": 0.20, ... }
  ],
  "consensus_classification": "brute_force",
  "agreement_score": 0.87,
  "disagreement_summary": "Local model classified as network_intrusion (0.20 weight)",
  "final_recommendation": "...",
  "weights_used": { "openai": 0.45, "anthropic": 0.35, "local": 0.20 }
}
```

**UI description:** A "Consensus Engine" tab in the war room showing a per-model output table (model, weight pill, classification, severity, confidence bar, key findings), an agreement score radial gauge, a disagreement summary card, and the final weighted recommendation panel. If a model is unavailable, its row shows a grey "unavailable" badge and the weights column shows the redistributed values.

---

### Feature 25 — AI SOC Digital Twin Simulator

**Problem it solves:** Platform validation and analyst training require realistic, repeatable attack scenarios that do not affect production data or metrics. The built-in simulation mode uses fixed scenarios; the digital twin adds automated accuracy measurement and comparative analysis.

**Implementation approach:** The `DigitalTwinService` maintains six `_BUILTIN_SCENARIOS` (phishing, malware, ddos, insider, brute_force, exfiltration) and per-type `_SCENARIO_TEMPLATES` containing IP ranges, protocols, attack names, and asset types. `_generate_synthetic_incidents()` creates randomised incidents from templates. `_simulate_agent_response()` samples 85–95% correct classifications to simulate realistic agent accuracy. Results are stored in `digital_twin_runs` and compared against the scenario's `expected_mitre_technique` and `expected_response`.

**API contract:**
```
GET /api/v1/digital-twin/scenarios
Response: { "scenarios": [ { "id": "scenario-phishing", "name": "Phishing Campaign",
  "scenario_type": "phishing", "severity": "high", "difficulty": "medium",
  "expected_mitre_technique": "T1566.001", "incident_count": 5 } ] }

POST /api/v1/digital-twin/run/{scenario_id}
Response: {
  "run_id": "uuid",
  "accuracy_score": 91,
  "response_quality_score": 88,
  "comparison_summary": "Excellent: 91% accuracy on 5 synthetic incidents.",
  "agent_responses": [
    { "incident_id": "SIM-0", "classification": "phishing",
      "expected_classification": "phishing", "correct": true, "confidence": 0.89 }
  ],
  "recommendations": []
}

GET /api/v1/digital-twin/runs/{run_id}   → retrieve a past run
POST /api/v1/digital-twin/compare        → compare two run IDs side-by-side
```

**UI description:** The `/digital-twin` page shows six scenario cards in a responsive grid. Each card displays the scenario icon, difficulty badge (easy / medium / hard), severity, MITRE technique, attack type, and synthetic incident count. A "Run Simulation" button fires the simulation; on completion, the card shows an inline result: accuracy bar chart, response quality percentage, and a row of green/red dots representing per-incident classification outcomes.

---

### Feature 26 — Cost Intelligence Platform

**Problem it solves:** Enterprise AI deployments require visibility into per-workflow, per-model, and per-user token consumption and costs to control spending, identify optimisation opportunities, and demonstrate ROI.

**Implementation approach:** `CostIntelligenceService.log_usage()` is called by every service that makes LLM calls, recording model name, prompt/completion tokens, estimated cost (from `_COST_RATES` per-model pricing), cache hit status, Redis cache savings, and memory reuse savings. The `estimate_cost()` function uses a dict of per-model input/output rates (e.g., `gpt-4.1-mini`: $0.00015/$0.00060 per 1K tokens). Six read endpoints aggregate these records for dashboarding. Five built-in optimisation suggestions are generated based on the usage pattern (e.g., "Switch to gpt-4.1-mini for classification tasks to reduce cost by ~40%").

**API contract:**
```
GET /api/v1/cost/summary?days=30
Response: { "total_cost": 12.47, "total_tokens": 1842000, "total_calls": 847,
            "avg_cost_per_call": 0.0147, "date_range": "2026-05-11 to 2026-06-10" }

GET /api/v1/cost/by-agent     → { "agents": [ { "agent_name": "...", "total_cost": ... } ] }
GET /api/v1/cost/by-model     → { "models": [ { "model_name": "...", "total_cost": ... } ] }
GET /api/v1/cost/by-workflow  → { "workflows": [ { "workflow_name": "...", "total_cost": ... } ] }
GET /api/v1/cost/by-user      → { "users": [ { "user_id": "...", "total_cost": ... } ] }
GET /api/v1/cost/savings      → { "redis_savings": 3.21, "memory_reuse_savings": 1.45,
                                   "total_savings": 4.66, "savings_rate": 0.27 }
```

**UI description:** The `/cost-intelligence` page provides: (1) a day-range selector (7 / 30 / 90 days); (2) four KPI cards (Total Cost, Total Tokens, Avg Cost/Call, Total Savings); (3) savings breakdown cards (Redis Cache, Memory Reuse, RAG Deduplication); (4) a Recharts BarChart showing cost by agent; (5) a PieChart showing cost distribution by model; (6) a LineChart showing 14-day cost trend; (7) an optimisation suggestions table with priority badges (high / medium / low), estimated savings, and implementation effort indicators.
