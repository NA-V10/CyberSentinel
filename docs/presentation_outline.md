# CyberSentinel AI — 10-Minute Technical Presentation Outline

**Total runtime:** 10 minutes  
**Audience:** Technical audience (engineers, security practitioners, technical managers)  
**Format:** 10 slides, approximately 1 minute per slide except where noted

---

## Slide 1 (1 min) — Problem Statement

### Title: The SOC Analyst's Dilemma

**Key points:**
- Security Operations Centres receive thousands of SIEM alerts per day
- Manual triage takes 30–90 minutes per incident
- Institutional knowledge about similar past incidents is siloed in tickets and individual memory
- Junior analysts apply escalation criteria inconsistently — both under- and over-escalation
- No structured feedback loop: analyst assessments of AI suggestions are rarely captured to improve future recommendations

**Headline statistic:**
> The average mean time to detect (MTTD) a breach is 197 days; mean time to contain (MTTC) is 69 days. Manual triage is the bottleneck.

**The need:**
An AI assistant that retrieves relevant historical precedents, generates actionable response plans, makes escalation decisions consistently, and learns from analyst feedback over time — all in under 30 seconds.

---
**Speaker notes:**

Open with a concrete scenario: "Imagine it's 2 AM. Your on-call analyst gets paged about 500 failed SSH login attempts. They have to look up similar past incidents, draft a containment plan, decide whether to wake the SOC manager, and write an explanation — all manually. CyberSentinel AI does all of that automatically in under 30 seconds while the analyst reviews the output."

Emphasise that the pain is real and quantifiable — reference industry metrics on dwell time and analyst burnout.

---

## Slide 2 (1 min) — Architecture Overview

### Title: Full-Stack AI Platform

**Visual:** Simplified layer diagram (reference `architecture.md`)

**Four layers:**
1. **Frontend** — Next.js 14 with Clerk authentication, dark cybersecurity theme, real-time animated UI
2. **Backend** — FastAPI :8000, LangGraph multi-agent workflow, RAG pipeline, Graph service, ML predictor, WebSocket streaming
3. **Data** — PostgreSQL (relational) + Qdrant (vector) + Neo4j (knowledge graph) + Redis (cache)
4. **AI** — OpenAI GPT-4.1-mini (reasoning) + text-embedding-3-small (1536-dim vectors)

**Key architectural decisions:**
- MCP server on :8001 for standardised tool access (Claude Desktop compatible)
- Hybrid retrieval: 0.7 × semantic + 0.3 × keyword fusion
- Guardrails layer: 19 prompt-injection patterns + output credential sanitisation

---
**Speaker notes:**

Walk through the diagram top-to-bottom. Stress the "three data stores" differentiation — each serves a purpose the others cannot: Postgres for transactional integrity, Qdrant for semantic similarity, Neo4j for structural relationship traversal. Don't deep-dive here; subsequent slides cover each component.

---

## Slides 3–4 (2 min) — RAG + Graph RAG

### Slide 3 Title: Hybrid Retrieval — Finding What Matters

**The three-strategy approach:**

| Strategy | Technology | Weight |
|----------|-----------|--------|
| Semantic search | Qdrant (text-embedding-3-small) | 0.7 |
| Keyword search | PostgreSQL `plainto_tsquery` | 0.3 |
| Graph expansion | Neo4j Cypher traversal | Augments |

**Why hybrid?**
- Pure vector search misses exact matches (IP addresses, CVE IDs, port numbers)
- Pure keyword search misses semantic similarity ("brute force" ≠ "credential stuffing" to a keyword index)
- Graph expansion adds structural knowledge: "this attack type is MITIGATED_BY these controls"

**Citation system:**
- Every retrieved incident receives a `[REF-N]` label
- LLM is instructed to cite evidence using these labels
- Frontend renders citations with incident ID, score, severity, and attack type

---
**Speaker notes:**

Show the fusion formula on screen: `fused = 0.7 × semantic + 0.3 × keyword`. Explain that keyword scores are min-max normalised before fusion. Mention that metadata filtering (attack_type, severity) is pushed into the Qdrant index layer for efficiency, not post-filtered.

---

### Slide 4 Title: Graph RAG — Structural Knowledge

**Neo4j knowledge graph schema (simplified):**

```
(Incident) -[:INCIDENT_OF_TYPE]-> (AttackType)
(AttackType) -[:MITIGATED_BY]-> (Mitigation)
(Incident) -[:TARGETS_ASSET]-> (Asset)
(Incident) -[:SIMILAR_TO {score}]-> (Incident)
```

**Demo query walkthrough:**
1. Incident classified as `brute_force`
2. Graph query: MATCH (at:AttackType {name: 'brute_force'})<-[:INCIDENT_OF_TYPE]-(i:Incident)
3. Returns 12 related incidents from the last 90 days
4. Second query: MATCH (at)-[:MITIGATED_BY]->(m:Mitigation) returns 6 known mitigation nodes
5. Both results are injected into the LLM context

**Confidence scoring:**
- Semantic similarity score: 0.0–1.0 (cosine)
- Judge quality score: 0.0–1.0 (normalised 0–10 scale)
- Both displayed in the frontend analysis card

---
**Speaker notes:**

Show a screenshot of the ReactFlow graph view with the central Incident node, connected AttackType, Asset, and Mitigation nodes. Explain that the graph grows with every ingested incident — it's not static knowledge, it's living organisational memory.

---

## Slides 5–6 (2 min) — Multi-Agent Workflow

### Slide 5 Title: Eight Agents, One State Machine

**LangGraph workflow topology:**

```
START → Validation → Classification → Retrieval → Mitigation
     → Escalation → Explainability → Judge ──→ (retry) → Mitigation
                                          └──→ AssembleFinal → Feedback → END
```

**Agent responsibilities:**

| Agent | Role | LLM? |
|-------|------|------|
| ValidationAgent | Guardrails: length, IP format, prompt injection | No |
| ClassificationAgent | 7-class threat classification + confidence | GPT-4.1-mini |
| RetrievalAgent | Hybrid RAG + Graph expansion | Embeddings |
| MitigationAgent | 4-phase response plan (containment/eradication/recovery/prevention) | GPT-4.1-mini |
| EscalationAgent | L1 / L2 / L3 / SOC_Manager decision | No (rule-based) |
| ExplainabilityAgent | 3–5 paragraph professional explanation | GPT-4.1-mini |
| JudgeAgent | Quality + Safety + Completeness + Hallucination assessment | GPT-4.1-mini |
| FeedbackAgent | Async Postgres persistence (non-blocking) | No |

---
**Speaker notes:**

Emphasise the type-safety of LangGraph: AgentState is a TypedDict — each agent receives the full shared state and returns a partial update dict. The compiled graph handles routing. This makes each agent independently testable.

---

### Slide 6 Title: LLM-as-Judge + Retry Logic

**Judge evaluation dimensions:**

| Dimension | Scale | Threshold |
|-----------|-------|-----------|
| Quality score | 0–10 | Retry if < 5 |
| Safety | boolean | Retry if false |
| Completeness | 0–10 | Informational |
| Hallucination risk | low/medium/high | High → penalise quality by 2 |

**Retry loop:**
- If `is_safe = false` or `quality_score < 5`: increment `retry_count`, route back to MitigationAgent
- Maximum 1 retry (prevents infinite loops)
- Both `judge_score` and `judge_feedback` are included in the final API response

**WebSocket streaming of agent steps:**
Each agent sends a typed status message (`{type, step, message}`) through the shared WebSocket connection. The frontend renders an animated timeline showing each step as it completes. The analyst sees live progress rather than a loading spinner.

---
**Speaker notes:**

Mention that the rule-based fallback for the JudgeAgent means the quality gate is always active, even if the OpenAI API is temporarily unavailable. Show the WebSocket message format briefly: the step enum maps directly to UI timeline entries.

---

## Slide 7 (1 min) — MCP Server

### Title: Standardised Tool Access via MCP

**What is MCP?**
Model Context Protocol — Anthropic's open standard for connecting AI models to external tools and data sources. Claude Desktop and other MCP clients can call CyberSentinel tools natively.

**8 tools exposed:**

| Tool | Key Use Case |
|------|-------------|
| `search_similar_incidents` | Find historical precedents via hybrid RAG |
| `get_incident_by_id` | Pull full incident record by UUID |
| `get_attack_type_context` | MITRE ATT&CK tactics + patterns for any attack type |
| `recommend_mitigation` | Generate or retrieve 4-phase mitigation plan |
| `calculate_risk_score` | Composite risk score: impact + likelihood + asset criticality |
| `create_incident_report` | Structured executive report with timeline |
| `query_graph_relationships` | Neo4j subgraph traversal |
| `store_feedback` | Analyst rating submission |

**Transports:** stdio (Claude Desktop) + HTTP (:8001)

**Fallback:** All tools degrade gracefully to a static knowledge base when the backend is unreachable, ensuring the MCP server is always usable.

---
**Speaker notes:**

Explain that the MCP server enables a separate usage pattern: analysts can use Claude Desktop or any MCP-compatible client to interactively query the CyberSentinel knowledge base using natural language. The same backend APIs serve both the web UI and the MCP clients — no duplication.

---

## Slide 8 (1 min) — Real-time SaaS UI

### Title: Analyst-First Interface

**Design principles:**
- Dark cybersecurity theme (consistent with industry tooling expectations)
- Information density without clutter — structured cards for each analysis section
- Live feedback: animated agent timeline during analysis, no long loading waits
- Role-based rendering — admin features hidden from analyst accounts

**Key UI components:**

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Agent timeline | Framer Motion animations | Shows each agent step completing in real time |
| Graph visualisation | ReactFlow + custom node types | Interactive Neo4j subgraph exploration |
| Analysis cards | Radix UI + Tailwind CSS | Threat class, confidence, escalation, citations |
| Incident table | TanStack Table | Sortable, filterable historical incidents |
| Charts | Recharts | Severity distribution, attack type breakdown |

**Roles and access:**
- `analyst`: Analyze + Search + Graph + Feedback + own Memory
- `manager`: Analyst capabilities + Feedback Stats across all users
- `admin`: All capabilities + Data ingestion + Index management

---
**Speaker notes:**

If doing a live demo, walk through the UI quickly: landing page → sign in → dashboard → new incident analysis → watch the timeline animate → expand the mitigation cards → click "Graph View" to see the Neo4j relationships rendered in ReactFlow.

---

## Slides 9–10 (2 min) — Demo + Q&A

### Slide 9 Title: Live Demo — SSH Brute Force

**Demo walkthrough (approximately 90 seconds):**

1. **Open the dashboard** — show recent incidents overview, severity distribution chart
2. **New analysis** — paste the sample incident:
   ```
   Multiple failed SSH login attempts from 192.168.1.25 targeting 10.0.0.5 over TCP port 22.
   Over 500 failed attempts in the last 10 minutes. Severity: High. Source IP repeated across
   multiple destination hosts in the subnet.
   ```
3. **Watch the WebSocket timeline** — validation → classification → retrieval → mitigation → escalation → explanation → judge
4. **Review the output sections:**
   - Threat class: `brute_force` (93% confidence)
   - 5 similar historical incidents with `[REF-1]` through `[REF-5]` citations
   - Mitigation plan: 4 expandable phases
   - Escalation: `L3` with reason
   - Explanation: 4-paragraph professional analysis
   - Judge score: 0.91 | Safe: true
5. **Click Graph View** — show the ReactFlow graph with the brute_force AttackType, TARGETS_ASSET (192.168.1.25, 10.0.0.5), and MITIGATED_BY nodes
6. **Submit feedback** — analyst rates the response 4/5, marks `mitigation_worked = true`

**Key callouts during demo:**
- Point out the real-time WebSocket updates as each agent completes
- Show the `[REF-N]` citations in the similar incidents list
- Highlight the escalation reason string — it's human-readable, not just a label
- Show the judge score in the response metadata

---
**Speaker notes:**

Keep this tight. If the live demo has any issues, fall back to screenshots. The most important things to show are: (1) the live agent timeline, (2) the citation system, and (3) the structured mitigation output. Everything else is secondary.

---

### Slide 10 Title: Summary + Q&A

**What we built:**

| Capability | How |
|-----------|-----|
| AI incident analysis | LangGraph 8-agent workflow |
| Historical context | Hybrid RAG: Qdrant + PostgreSQL FTS + Neo4j |
| Structural knowledge | Neo4j Graph RAG |
| Real-time updates | FastAPI WebSocket + ConnectionManager |
| ML second opinion | RandomForest on network flow features |
| Quality assurance | LLM-as-Judge with retry loop |
| Tool ecosystem | MCP server with 8 tools |
| Safety | Guardrails: 19 injection patterns + output sanitisation |

**Stack summary:**

| Layer | Technology |
|-------|----------|
| Frontend | Next.js 14, Clerk, ReactFlow, Recharts, Framer Motion |
| Backend | FastAPI, LangGraph, SQLAlchemy, asyncpg |
| AI | GPT-4.1-mini, text-embedding-3-small |
| Databases | PostgreSQL, Qdrant, Neo4j, Redis |
| MCP | Python MCP SDK, stdio + HTTP |

**Q&A**

Anticipated questions and talking points:
- *Why not a single LLM call?* — Specialised agents with defined responsibilities produce higher-quality, more auditable outputs. Each agent's output is independently inspectable in the state.
- *How accurate is the classification?* — The LLM classification achieves high accuracy on well-described incidents. The ML predictor provides a statistical cross-check. The JudgeAgent catches hallucinations.
- *How do you handle GDPR / data sensitivity?* — Incidents are scoped per user_id. Role-based access controls data visibility. Output sanitisation prevents credential leakage.
- *What does scaling look like?* — The FastAPI backend is stateless; multiple instances can run behind a load balancer. Qdrant and Neo4j support clustering for high availability.

---
**Speaker notes:**

Close with the core value proposition: "CyberSentinel AI turns a 45-minute manual triage process into a 30-second AI-assisted analysis, with full citations, a four-phase response plan, a consistent escalation decision, and a quality score — all in one response." Then open for questions.

---

## Advanced Differentiators (v2 Features)

**Version:** 2.0  
**Audience note:** This section is intended for extended presentations (15–20 minutes) or as a leave-behind for technical evaluators. It covers all twenty advanced capabilities introduced in CyberSentinel AI v2 that differentiate the platform from first-generation AI-assisted triage tools.

---

| # | Feature | One-Line Description | Business Value |
|---|---------|---------------------|----------------|
| 1 | **MITRE ATT&CK Mapping** | Every incident automatically mapped to tactic, technique, and ATT&CK ID | Enables industry-standard threat communication, regulatory reporting, and cross-team intelligence sharing without manual framework lookups |
| 2 | **AI Incident War Room** | Realtime collaborative investigation workspace at `/war-room/{id}` with live agent timeline and multi-analyst support | Replaces fragmented tooling (SIEM + chat + tickets) with a single, persistent investigation environment; reduces analyst context-switching overhead |
| 3 | **Human-in-the-Loop Approval** | Structured approve / reject / edit / escalate workflow before any mitigation is actioned | Preserves human accountability and legal defensibility; prevents AI recommendations from being actioned without qualified review |
| 4 | **LLM-as-Judge Scorecard** | Multi-dimensional quality validation scoring correctness, safety, completeness, relevance, and hallucination risk | Gives analysts an objective confidence signal before they review AI output; prevents low-quality or unsafe recommendations from reaching the approval queue |
| 5 | **SOC Executive Dashboard** | Business-level KPIs at `/dashboard/executive` — MTTR, SLA breach rate, attack distribution | Provides SOC leadership with real-time visibility into operational performance without navigating raw incident data; supports board-level reporting |
| 6 | **Auto Incident Report Generator** | One-click Markdown and PDF report generation with executive summary, timeline, and signed findings | Eliminates 45–90 minutes of manual report writing per incident; produces consistent, auditable documentation for every case |
| 7 | **MITRE + Graph RAG Hybrid Reasoning** | Combined scoring formula fusing MITRE technique confidence with graph-based historical similarity | Improves analysis precision by combining two independent intelligence sources; reduces false classifications on novel attack variants |
| 8 | **Threat Intelligence Enrichment** | Automated IP reputation, domain classification, and file hash lookup in real time | Eliminates manual indicator lookups across multiple threat intelligence portals; enrichment results are captured in the audit trail |
| 9 | **Risk Scoring Engine** | Explainable 0–100 composite score: impact × 0.40 + likelihood × 0.35 + asset criticality × 0.25 | Replaces subjective severity labels with an objective, defensible risk score that drives prioritisation and SLA assignment |
| 10 | **Continuous Feedback Learning** | Analyst rating and mitigation-effectiveness signals captured and converted to procedural memory | Creates a self-improving knowledge base that incorporates organisational experience into future incident recommendations |
| 11 | **Policy-Aware Guardrails** | Offensive cyber action blocking and configurable per-org policy rules beyond standard prompt injection | Prevents misuse of the AI platform for offensive purposes; enables organisations to enforce their acceptable use policies at the API layer |
| 12 | **Advanced Memory Scopes** | Five-scope memory isolation: user / incident / org / mitigation / false-positive | Enables precise contextual recall appropriate to each scope; prevents false-positive patterns from one analyst contaminating another's recommendations |
| 13 | **Realtime WebSocket Agent Progress** | Per-step streaming with named agent nodes, percentage progress, and elapsed time | Builds analyst trust by making the AI pipeline transparent; reduces perceived latency through progressive disclosure |
| 14 | **Playbook Generator** | Automated, customisable incident response playbooks with role assignments and time estimates | Accelerates incident response execution by converting AI analysis into actionable, structured playbooks that teams can follow step-by-step |
| 15 | **Simulation Mode** | `/simulation` — select predefined scenarios and run the full pipeline in a sandboxed environment | Enables safe platform validation, analyst training, compliance demonstrations, and regression testing without affecting production data or metrics |
| 16 | **Explainability Panel** | Inline reasoning traces showing why each agent reached its decision, with linked evidence citations | Builds analyst trust and supports skill development by making the AI's reasoning process transparent and auditable |
| 17 | **Escalation SLA Tracker** | Automated SLA deadline assignment, breach alerting, and compliance tracking | Ensures consistent, time-bound incident response; SLA compliance data feeds directly into executive reporting and contractual commitments |
| 18 | **Secure Audit Logs** | Tamper-evident, append-only log of all analyst actions, AI decisions, and system events | Satisfies SOC 2 / ISO 27001 audit evidence requirements; provides a complete forensic record for post-incident review and insider threat investigation |
| 19 | **Multi-Tenant SaaS Support** | Clerk org isolation with per-org data scoping across all databases and memory stores | Enables managed security service providers to serve multiple clients from a single deployment with complete data isolation and per-client configuration |
| 20 | **MCP Tool Marketplace** | `/mcp-tools` — browse, test, and manage MCP-exposed cybersecurity tools from the UI | Makes the platform extensible and composable; security teams can integrate CyberSentinel AI capabilities into any MCP-compatible workflow, including Claude Desktop |

---

### Extended Speaker Notes — v2 Differentiators Slide

When presenting these features to a technical audience, cluster them into four capability themes:

**1. Intelligence Quality (Features 1, 7, 8, 12)**
MITRE mapping, hybrid reasoning, threat enrichment, and advanced memory scopes all address the same root problem: the quality of context available to the AI. These features collectively mean the platform is reasoning from richer, more accurate inputs than any single-database retrieval approach.

**2. Human Control and Accountability (Features 3, 4, 11, 18)**
Human-in-the-loop approval, the LLM judge scorecard, policy-aware guardrails, and secure audit logs address enterprise concerns about AI autonomy and compliance. These are the features that turn CyberSentinel AI from a demo into a platform that passes a security review board.

**3. Analyst Experience and Productivity (Features 2, 6, 13, 14, 15, 16)**
The war room, report generator, realtime streaming, playbook generator, simulation mode, and explainability panel all address analyst workflow. These are the features that matter to the people using the platform every day — and that determine adoption rates.

**4. Enterprise Operations and Scale (Features 5, 9, 10, 17, 19, 20)**
The executive dashboard, risk scoring engine, feedback learning, SLA tracker, multi-tenancy, and MCP marketplace address the concerns of the buyer: ROI measurement, organisational learning, compliance, and architectural extensibility.

Framing the twenty features this way — four themes of five — makes a complex feature set immediately comprehensible to any audience.
