# CyberSentinel AI — 15-Minute Panel Demo Script

**Total runtime:** 15 minutes  
**Audience:** Technical and executive panel (engineers, SOC practitioners, technical managers, investors)  
**Format:** Live demo with narrated walkthrough — 7 scenes  
**Prerequisite:** Platform running at `http://localhost:3000`, backend at `http://localhost:8000`, sample dataset ingested, signed in as an analyst account

---

## Pre-Demo Checklist

- [ ] Docker Compose services all healthy (`docker compose ps`)
- [ ] Sample dataset ingested (`/api/v1/ingest/build-index` completed successfully)
- [ ] Browser logged into CyberSentinel AI at `http://localhost:3000`
- [ ] Browser zoom at 100%, dark mode enabled
- [ ] Terminal hidden / background processes closed
- [ ] One browser tab open for each scene (pre-navigate to reduce switching time)

---

## Scene 1 — Security Operations Dashboard (2 minutes)

### Navigation
Open: `http://localhost:3000/dashboard`

### What to Show
- The main dashboard loads with the dark cybersecurity theme — a full-width header bar showing the CyberSentinel AI logo, the authenticated analyst's name, and the organisation switcher
- The top row displays four KPI summary cards:
  - **Total Incidents** (e.g., 1,247 this month)
  - **Critical Open** (e.g., 8 requiring immediate attention)
  - **Avg. MTTR** (e.g., 18.4 minutes — AI-assisted vs. 67 minutes industry average)
  - **SLA Compliance** (e.g., 93.2%)
- Below the KPIs: a stacked bar chart showing incident volume by severity over the past 30 days, and a donut chart showing attack type distribution (brute_force, malware, phishing, ddos, network_intrusion)
- A scrollable recent incidents table showing the last 10 incidents with status badges, severity colour coding, and timestamps

### What to Say
*"Welcome to CyberSentinel AI — an enterprise-grade, AI-powered incident response platform built for modern Security Operations Centres. This is the Security Operations Dashboard — the nerve centre for your analyst team.*

*At a glance, the SOC sees 1,247 incidents processed this month, with an average mean time to respond of 18.4 minutes. The industry average for manual triage is over 67 minutes. That gap — 49 minutes per incident — represents the business value CyberSentinel AI delivers.*

*The attack type distribution shows that brute force and malware incidents dominate this month's workload. The SLA compliance rate is 93.2% — we'll show you how the platform enforces that later.*

*Rather than walking through static charts, let me show you the platform in action. We're going to run a complete incident analysis — from raw threat description to approved, signed report — in the next 13 minutes."*

---

## Scene 2 — Simulation Mode: Ransomware Infection Scenario (3 minutes)

### Navigation
Open: `http://localhost:3000/simulation`

### What to Show
1. The simulation page displays a grid of predefined attack scenario cards:
   - **Ransomware Infection** — Impact, T1486, Critical
   - **DDoS Volumetric Attack** — Impact, T1498, High
   - **Credential Stuffing Campaign** — Credential Access, T1110, High
   - **Phishing with Payload** — Initial Access, T1566, Medium
   - **Lateral Movement Detection** — Lateral Movement, T1021, High
2. Click the **Ransomware Infection** card — it expands to show the scenario description and pre-fills the incident form
3. The pre-filled incident text reads:
   ```
   Multiple endpoints on the corporate network (10.0.10.15, 10.0.10.22, 10.0.10.31)
   have encrypted their local file systems. Ransom note files named
   "YOUR_FILES_ARE_ENCRYPTED.txt" are present on each host. Process analysis shows
   vssadmin.exe deleting shadow copies. Outbound C2 connection detected to
   91.108.4.1:443. Severity: Critical.
   ```
4. Click **Run Simulation** — the platform navigates automatically to the war room at `/war-room/{generated_id}`
5. The agent timeline begins streaming immediately — each step pulses in sequence:
   - Validating input... (checkmark appears in ~1 second)
   - Classifying threat... (GPT-4.1-mini classifies: `malware`, confidence 0.97)
   - Searching similar incidents... (6 historical ransomware precedents retrieved)
   - Mapping to MITRE ATT&CK... (T1486 — Data Encrypted for Impact, Tactic: Impact)
   - Enriching threat intelligence... (91.108.4.1 verdict: malicious, tagged as known C2)
   - Generating mitigation... (4-phase playbook generated)
   - Calculating risk score... (score: 94/100)
   - Determining escalation... (SOC_Manager)
   - Generating explanation... (4-paragraph professional explanation)
   - Judge evaluating quality... (composite: 9.1/10, Safe: true)
   - Analysis complete.

### What to Say
*"Instead of typing a raw incident description, I'm going to use Simulation Mode — a feature that lets security teams validate platform behaviour against realistic, predefined attack scenarios. This is invaluable for training exercises, compliance demonstrations, and regression testing after system updates.*

*I'm selecting the Ransomware Infection scenario — one of the most destructive attack types a SOC faces. Notice the incident details are pre-loaded: multiple endpoints with encrypted file systems, shadow copy deletion via vssadmin.exe — a hallmark of ransomware — and an outbound C2 connection already detected.*

*Clicking Run Simulation fires the full CyberSentinel AI multi-agent pipeline. Watch the Agent Timeline on the right — each node represents a specialised AI agent completing its task in sequence. We have eight agents: validation, classification, retrieval, MITRE mapping, threat enrichment, mitigation, risk scoring, escalation, explainability, and the LLM-as-Judge quality gate.*

*The classification came back immediately: malware, 97% confidence. The MITRE ATT&CK mapping is T1486 — Data Encrypted for Impact. The threat intelligence enrichment flagged the C2 IP as a known malicious actor. And the risk score is 94 out of 100 — this is a critical incident. The full pipeline completed in under 30 seconds."*

---

## Scene 3 — AI Incident War Room: Deep Dive (3 minutes)

### Navigation
Already in the war room at `/war-room/{incident_id}` from Scene 2

### What to Show

**Evidence Panel tab (default):**
- The top section shows incident metadata: timestamp, severity badge (Critical — red), source/destination IPs, protocol
- The raw incident text is displayed in a formatted card
- Analyst notes field (empty — show that analysts can add contextual notes)

**MITRE ATT&CK tab:**
- Navigate to the MITRE tab
- Show the ATT&CK matrix heatmap with the **Impact** tactic column highlighted
- The **T1486 — Data Encrypted for Impact** technique cell is highlighted in red
- The detail card below shows: Technique ID T1486, full name, description excerpt, sub-techniques (T1486.001), confidence 0.94, and a direct link to attack.mitre.org
- Scroll down to show a second mapping: **T1490 — Inhibit System Recovery** (shadow copy deletion)

**Risk Score tab:**
- Navigate to the Risk Score tab
- A large semicircular gauge displays **94 / 100** in the red zone
- Below the gauge: factor breakdown table
  - Impact: 97 / 100 — "Critical severity ransomware affecting multiple production endpoints"
  - Likelihood: 95 / 100 — "97% threat confidence, confirmed C2 communication"
  - Asset Criticality: 88 / 100 — "Corporate workstations with access to shared file systems"

**Threat Intel tab:**
- Navigate to the Threat Intel tab
- A table shows the enriched indicators:
  - `91.108.4.1` — verdict: **Malicious** (red badge), confidence 0.94, tags: `c2-server`, `ransomware-infrastructure`
  - `vssadmin.exe` (process hash) — verdict: **Clean** (the binary itself is legitimate; the context is malicious — use this to make a point about contextual analysis)
  - The ransom note filename pattern — verdict: **Malicious** (known ransomware indicator)

### What to Say
*"This is the AI Incident War Room — CyberSentinel AI's real-time investigation workspace. Multiple analysts can be in this room simultaneously, all seeing the same live data. It's designed to replace the fragmented experience of jumping between SIEM, ticketing systems, and chat tools.*

*Let me take you through the key panels. The MITRE ATT&CK tab shows us exactly where this attack sits in the adversary kill chain. We have two technique mappings: T1486 — Data Encrypted for Impact, which is the ransomware payload itself, and T1490 — Inhibit System Recovery, the shadow copy deletion. This mapping was generated automatically — no analyst looked it up.*

*The Risk Score is 94 out of 100. This isn't a single number pulled from a severity field — it's a composite score with three independently assessed factors: impact at 97, likelihood at 95, and asset criticality at 88. Every factor is explained in plain English, which means a manager reading this report understands exactly why the risk is this high.*

*The Threat Intel tab shows the enrichment results. The C2 IP at 91.108.4.1 was automatically flagged as malicious with 94% confidence, tagged as ransomware infrastructure. That enrichment happened in real time as part of the analysis pipeline — no manual lookup required."*

---

## Scene 4 — Human-in-the-Loop Approval and LLM Judge Scorecard (2 minutes)

### Navigation
Still in the war room — scroll down to the **Approval Panel** section, or click the Approval tab if tabbed

### What to Show
1. The Approval Panel header shows: **Status: Pending Review** — amber badge
2. The **LLM-as-Judge Scorecard** card displays five progress bars:
   - Correctness: **9.1 / 10** (green)
   - Safety: **Pass** (green checkmark)
   - Completeness: **8.8 / 10** (green)
   - Relevance: **9.0 / 10** (green)
   - Hallucination Risk: **Low** (green)
   - Composite Score: **9.0 / 10** — "Analysis is well-grounded in retrieved evidence and MITRE framework. Mitigation plan is comprehensive and specific to the observed indicators."
3. Below the scorecard: four action buttons — **Approve**, **Reject**, **Edit**, **Escalate**
4. Click **Approve** — a confirmation dialog appears: "Confirm approval of this incident analysis and mitigation plan"
5. Click Confirm — the status badge changes immediately to **Approved** (green)
6. A toast notification confirms: "Incident analysis approved by [Analyst Name] at 14:23:07"
7. Point to the bottom of the panel: "This approval decision has been recorded in the tamper-evident audit log"

### What to Say
*"This is one of the most important features in an enterprise AI platform: Human-in-the-Loop approval. AI recommendations do not automatically trigger action. Every analysis goes through a structured review gate.*

*Before the analyst makes their decision, they see the LLM-as-Judge scorecard. A separate AI model — acting as a quality judge — has independently evaluated the analysis across five dimensions: correctness, safety, completeness, relevance, and hallucination risk. Everything is scoring at 9 out of 10 today — this is a high-quality analysis.*

*The safety check is non-negotiable. If the AI produced advice that was dangerous, offensive, or legally problematic, the judge would flag it and the system would automatically retry. That retry mechanism ran silently in the background before this analysis was even presented to you.*

*The analyst clicks Approve. The mitigation plan is now authorised. This decision — who approved it, when, and what the judge scorecard showed — is permanently recorded in the audit log. That's your SOC 2 evidence, right there."*

---

## Scene 5 — Incident Report Generation (2 minutes)

### Navigation
Click the **Reports** tab in the war room, or navigate to `http://localhost:3000/reports`

### What to Show
1. In the war room toolbar, click **Generate Report** button
2. A loading indicator appears for 2–3 seconds
3. The view splits into two panes:
   - **Left pane**: Markdown preview with syntax highlighting, showing:
     - `# Incident Analysis Report`
     - Executive Summary paragraph
     - Incident Details table (timestamp, severity, IPs, protocol)
     - MITRE ATT&CK Findings section (T1486, T1490)
     - Risk Assessment (score: 94/100 with factor table)
     - Threat Intelligence section (C2 IP enrichment)
     - Mitigation Plan (all four phases with numbered steps)
     - Escalation Decision and SLA
     - Judge Scorecard table
     - Approval record (approved by, timestamp)
     - Appendix: Similar Incidents [REF-1] through [REF-6]
   - **Right pane**: PDF preview iframe showing the formatted, paginated document with the CyberSentinel AI logo header and report ID footer
4. Show the toolbar with two buttons: **Download Markdown** and **Download PDF**
5. Click **Download PDF** — the browser triggers a file download named `incident-report-{id}-2026-06-09.pdf`

### What to Say
*"Every approved incident can be turned into a signed, professional report with a single click. This is the report generator.*

*The left pane shows the Markdown source — structured, version-controllable, ready to commit to your incident response repository. The right pane shows the formatted PDF — what you'd share with management, legal, or an auditor.*

*Notice what's in this report: the executive summary, the full MITRE ATT&CK analysis, the risk score with factor breakdown, the threat intelligence findings, the complete four-phase mitigation plan, the escalation decision, the LLM judge scorecard, and the approval record with the analyst's identity and timestamp. Everything that went into this analysis is documented and attributed.*

*This report took about two seconds to generate. The alternative — an analyst writing this manually — would take 45 to 90 minutes. And every report would look different. CyberSentinel AI makes every report consistent, complete, and instant."*

---

## Scene 6 — SOC Executive Dashboard (2 minutes)

### Navigation
Open: `http://localhost:3000/dashboard/executive`

### What to Show
1. The executive dashboard loads with six KPI panels in a grid layout:
   - **MTTR Trend** — line chart showing mean time to respond over the last 30 days (target line at 20 minutes, current at 18.4 minutes — below target)
   - **SLA Breach Rate** — large gauge at 6.8%, colour-coded green (below 10% threshold)
   - **Attack Type Distribution** — donut chart with percentage breakdown: malware 31%, brute_force 26%, phishing 18%, ddos 14%, network_intrusion 11%
   - **Incidents by Severity** — stacked bar chart showing this week vs. last week: Critical dropped from 12 to 8
   - **Analyst Workload** — heat map showing open incident count per analyst with colour intensity
   - **Weekly Incident Volume** — area chart with trend over 12 weeks
2. Point to the date range picker in the top right — explain that all charts can be filtered by custom date ranges and by organisation (for multi-tenant deployments)
3. Highlight the MTTR figure: "18.4 minutes — this is our headline metric"

### What to Say
*"This is the SOC Executive Dashboard — designed for SOC managers, CISOs, and board-level reporting. It aggregates everything happening in the platform into business-level metrics.*

*The headline number here is MTTR: 18.4 minutes mean time to respond. That's the time from incident submission to an approved, documented response. The industry benchmark for manually triaged incidents is 67 minutes. We are delivering a 3.6× improvement.*

*The SLA breach rate is 6.8% — meaning 93.2% of incidents were addressed within their assigned SLA window. The platform automatically assigns SLA deadlines based on severity and escalation level, tracks them in real time, and alerts analysts before a breach occurs.*

*The attack type distribution gives the security leadership team a clear picture of the threat landscape this month. Malware and brute force are dominating — that drives investment decisions: where to allocate analyst capacity, which detection rules need tuning, which vendor controls need upgrading.*

*This dashboard can be scoped to a specific date range or a specific organisation. For managed security service providers running multiple client environments, each client's executive team sees only their own data — completely isolated through our multi-tenant architecture."*

---

## Scene 7 — MCP Tool Marketplace (1 minute)

### Navigation
Open: `http://localhost:3000/mcp-tools`

### What to Show
1. The MCP Tool Marketplace page loads with a grid of tool cards
2. Visible tools include:
   - `search_similar_incidents` — Hybrid RAG search over historical incidents
   - `get_incident_by_id` — Full incident record retrieval by UUID
   - `get_attack_type_context` — MITRE-mapped attack type information
   - `recommend_mitigation` — Four-phase mitigation plan generation
   - `calculate_risk_score` — Composite risk scoring
   - `create_incident_report` — Structured report generation
   - `query_graph_relationships` — Neo4j graph traversal
   - `store_feedback` — Analyst feedback submission
3. Click the `calculate_risk_score` card to expand it — show the parameter schema and example invocation
4. Point out the **MCP Server Status** indicator in the top right — green dot showing the MCP server is connected
5. Briefly show the inline test runner (no need to execute — just show the form)

### What to Say
*"The final stop on our tour: the MCP Tool Marketplace. MCP — the Model Context Protocol — is an open standard for connecting AI models to external tools and data sources. CyberSentinel AI exposes its core capabilities as MCP tools.*

*What this means in practice is that analysts using Claude Desktop, or any other MCP-compatible AI client, can query the CyberSentinel knowledge base directly using natural language — without opening the web interface. 'Search for brute force incidents from last month', 'Calculate the risk score for this incident', 'Get the mitigation plan for a ransomware attack' — all of these work as natural language commands in any MCP client.*

*The marketplace makes these tools discoverable and testable from within the platform itself. Security teams can extend the tool catalogue — adding integrations to SOAR platforms, threat feeds, or internal ticketing systems — and those tools are immediately available to every MCP-compatible workflow.*

*This extensibility is what makes CyberSentinel AI a platform, not just a product. You're not locked into our UI. Your analysts can work in whatever environment they prefer, and CyberSentinel AI's intelligence is always available to them."*

---

## Closing Statement

*"In 15 minutes, we've walked through the complete CyberSentinel AI lifecycle: from a raw ransomware incident description to an approved, signed incident report, with MITRE ATT&CK mapping, explainable risk scoring, threat intelligence enrichment, human-in-the-loop review, and executive-level reporting.*

*The platform is built on a foundation of enterprise-grade architecture: FastAPI with async multi-agent orchestration, hybrid retrieval across three database systems, real-time WebSocket streaming, multi-tenant Clerk authentication, and a compliance-ready audit trail.*

*CyberSentinel AI does not replace your analysts. It eliminates the low-value work — the lookups, the formatting, the framework cross-referencing — so your best people can focus on judgment calls that require human expertise.*

*We're happy to take questions."*

---

## Anticipated Questions and Talking Points

| Question | Talking Point |
|----------|--------------|
| *How accurate is the threat classification?* | LangGraph classification with GPT-4.1-mini achieves high accuracy on well-described incidents. The ML RandomForest classifier provides an independent second opinion. The LLM judge flags any response with low confidence or high hallucination risk before it reaches the analyst. |
| *What happens if the AI is wrong?* | Human-in-the-loop approval is the safety net. No recommendation is actioned without analyst sign-off. The Reject action requires a written reason that feeds into the continuous learning system. |
| *How do you handle sensitive incident data?* | All data is scoped to `user_id` and `org_id`. Role-based access controls enforce data visibility boundaries. Output sanitisation prevents credential leakage. Audit logs record all access events. |
| *Can we connect this to our existing SIEM?* | Yes — the MCP server provides a standard integration layer. SIEM output can be piped to the `/analyze/analyze-incident` endpoint programmatically. Playbook outputs can trigger SOAR actions. |
| *What does scaling look like?* | The FastAPI backend is stateless — multiple instances behind a load balancer. Qdrant, Neo4j, and PostgreSQL all support clustering. Redis provides shared session state for WebSocket fan-out in multi-instance deployments. |
| *How is multi-tenancy enforced?* | `org_id` is extracted from the Clerk JWT on every request. It is applied as a filter at the application layer on all database queries, Qdrant searches, and Neo4j traversals. No cross-org data access is possible through the API. |
| *What frameworks and compliance standards does this support?* | MITRE ATT&CK for threat taxonomy, SOC 2 / ISO 27001 through the tamper-evident audit log, and GDPR through per-user data scoping and the right-to-deletion workflow available through the admin interface. |
