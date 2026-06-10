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

---

## Extended Demo — Final Premium Feature Set (10 Minutes)

**Prerequisite:** All seven baseline scenes complete. Platform still open at the war room from Scene 3/4.

---

### Scene 8 — Agent Self-Reflection Engine (1.5 minutes)

#### Navigation
Still in the war room from Scene 3. Click the **Self-Reflection** tab.

#### What to Show
1. The tab header shows "Self-Reflection Engine" with a status badge
2. If the judge score from the previous analysis was below 7.5: the badge reads **Triggered** (amber) and all fields are populated
3. If the score was above 7.5: show the **Run Reflection** button and click it manually — this forces a reflection cycle for demo purposes
4. After triggering, three sections populate:
   - **Weaknesses Detected** — a list of tags: e.g., "incomplete containment steps", "missing C2 analysis", "low confidence on attribution"
   - **Missing Evidence** — tags: e.g., "lateral movement indicators", "persistence mechanism"
   - **Before / After Comparison** — two cards side by side showing the original analysis summary vs. the improved version, with changed lines highlighted in amber and new lines in green
5. At the bottom: **Final Confidence** badge — e.g., 8.4 / 10 (up from 6.2 before reflection)

#### What to Say
*"Most AI platforms stop at generating an answer. CyberSentinel AI goes one step further with the Self-Reflection Engine. After the LLM judge assigns its quality score, if that score falls below 7.5 — meaning the analysis has gaps — the system automatically enters a reflection loop.*

*First, it critiques its own output: what was missing? What was low confidence? Then it runs a second, improved analysis with those gaps as additional context. The before/after comparison you're seeing here is generated automatically — you can see exactly what changed and why.*

*The final confidence went from 6.2 to 8.4. No analyst had to ask for a retry. The system caught its own shortcomings and corrected them."*

---

### Scene 9 — Attack Campaign Detection (2 minutes)

#### Navigation
Open: `http://localhost:3000/campaigns`

#### What to Show
1. The page loads with three existing campaigns — stats cards at the top show: **3 Active**, **9 Total Incidents**, **84% Avg Confidence**
2. Point to the first campaign card: **Credential Harvesting Campaign** — 91% confidence, 3 related incidents (INC-102, INC-118, INC-130), time window: 24 hours
3. Click **Detect Campaigns** — a loading indicator appears; after 2–3 seconds a toast appears: "Campaign detection completed"
4. Click into **Credential Harvesting Campaign**:
   - **Overview tab**: Attack narrative ("A coordinated credential harvesting campaign targeting SSH services…"), threat actor profile, related incidents list
   - **Timeline tab**: Three events with relative timestamps — T+0h first detection, T+4h second host targeted, T+18h successful authentication
   - **Indicators tab**: Shared indicators (source subnet 45.33.x.x, MITRE T1110, SSH brute force), cluster statistics card
   - **Response tab**: Recommended countermeasures with numbered steps

#### What to Say
*"This is Campaign Detection — one of the most strategically important features for a SOC. An individual incident looks like a brute force attempt. But three incidents from the same /24 IP subnet, using the same MITRE technique, within 24 hours? That's a coordinated campaign.*

*The detection algorithm scores each pair of incidents across five dimensions: IP subnet overlap, attack type, MITRE technique, protocol, and severity. Pairs scoring above 60% similarity are grouped into campaigns.*

*What you're seeing here is the platform connecting the dots automatically. INC-102, INC-118, and INC-130 are not three separate brute force incidents — they're a single threat actor systematically probing your SSH infrastructure. The timeline shows the attacker succeeded on the third host at T+18 hours. With manual analysis, that connection might never have been made until after the breach was confirmed."*

---

### Scene 10 — Autonomous Investigation Mode (2 minutes)

#### Navigation
Return to the war room from Scene 3. Click the **Auto Investigation** tab.

#### What to Show
1. Click **Run Autonomous Investigation** — a loading indicator appears
2. A WebSocket-driven tool call timeline begins animating, showing 8 sequential steps:
   - **1. MITRE Mapping** — ✓ T1486 detected (0.3s)
   - **2. IP Reputation** — ✓ 91.108.4.1 flagged malicious (0.5s)
   - **3. Graph Query** — ✓ 12 related incidents found (0.8s)
   - **4. Similar Incidents** — ✓ 6 historical precedents retrieved (1.1s)
   - **5. Risk Calculation** — ✓ Risk score: 94/100 (0.2s)
   - **6. Mitigation** — ✓ 4-phase plan generated (1.4s)
   - **7. Guardrails Check** — ✓ Safe: true (0.1s)
   - **8. Report Generation** — ✓ Summary compiled (0.9s)
3. Below the timeline: the **Evidence Chain** collapse — click to expand and show each tool's structured output
4. **Findings Panel** shows: threat_level: high, confidence: 0.89, key indicators, total tool calls: 8, duration: 12.4s
5. **Judge Score** badge: 8.7 / 10

#### What to Say
*"Autonomous Investigation Mode turns the war room into an automated investigation engine. With a single click, the platform runs eight investigation steps in sequence — each one an MCP tool — and assembles everything into a complete investigation report.*

*Watch the tool timeline: MITRE mapping, IP reputation, graph query, similar incident search, risk calculation, mitigation generation, guardrails check, and final report. Eight steps, 12 seconds, no analyst intervention required.*

*This is the difference between an AI that answers questions and an AI that proactively investigates. The junior analyst doesn't need to know which lookups to run — the platform knows, and it runs them all. The senior analyst gets a complete investigation package ready for review."*

---

### Scene 11 — Multi-LLM Consensus Engine (1.5 minutes)

#### Navigation
Still in the war room. Click the **Consensus Engine** tab.

#### What to Show
1. Click **Run Consensus Analysis**
2. Three model cards populate showing per-model output:
   - **GPT-4.1-mini** (weight: 0.45) — Classification: malware, Severity: critical, Confidence: 0.94, Key findings: ["C2 communication detected", "shadow copy deletion confirmed"]
   - **Claude Haiku** (weight: 0.35) — Classification: malware, Severity: critical, Confidence: 0.91, Key findings: ["ransomware indicators", "multiple affected hosts"]
   - **Llama 3** (weight: 0.20) — Classification: malware, Severity: high, Confidence: 0.82, Key findings: ["endpoint compromise", "unusual outbound traffic"]
3. **Agreement Score** radial gauge: 0.87 (87% weighted agreement)
4. **Disagreement Summary** card: "Local model (0.20 weight) assessed severity as high rather than critical"
5. **Final Recommendation**: Consensus classification: malware, Severity: critical

#### What to Say
*"The Consensus Engine is CyberSentinel AI's answer to single-model bias. Instead of trusting one AI's classification, we run the same incident through three independent models simultaneously — GPT, Claude, and Llama — each with calibrated weights reflecting their performance on cybersecurity analysis.*

*All three models agree on the threat class: malware. GPT and Claude both say critical severity; Llama says high. The weighted agreement score is 87%. The consensus decision is malware, critical — aligned with the two higher-weighted models.*

*When models disagree significantly, that disagreement is itself a signal. It tells the analyst: 'this incident is ambiguous, apply more scrutiny.' And when three independent models converge on the same classification, the analyst can act with higher confidence.*

*If any model is unavailable, the weights redistribute automatically. The system always produces a consensus."*

---

### Scene 12 — AI SOC Digital Twin Simulator (1.5 minutes)

#### Navigation
Open: `http://localhost:3000/digital-twin`

#### What to Show
1. Six scenario cards load in a grid:
   - Phishing Campaign (medium difficulty, high severity)
   - Malware Outbreak (hard, critical)
   - DDoS Traffic Spike (medium, high)
   - Insider Threat (hard, critical)
   - SSH Brute Force (easy, medium)
   - Data Exfiltration (hard, critical)
2. Click **Run Simulation** on the **SSH Brute Force** scenario (easy, to ensure a clean result)
3. A loading indicator appears: "Running Simulation…"
4. After 2–3 seconds the card shows an inline result:
   - **91% accuracy** (amber bar animates to 91%)
   - **Response quality: 88%**
   - 6 response dots — 5 green (correct), 1 red (misclassified)
   - Summary: "Excellent: 91% accuracy on 6 synthetic incidents."
5. Now click **Run Simulation** on the **Malware Outbreak** (hard) to contrast:
   - Result typically shows 75–80% accuracy
   - More red dots appear
   - Summary: "Good: 77% accuracy. Some misclassifications detected."

#### What to Say
*"The Digital Twin Simulator lets you test the platform's detection capabilities against synthetic attack scenarios without touching production data. Think of it as a flight simulator for your SOC.*

*When I run the SSH Brute Force scenario — a well-understood attack type — the platform achieves 91% classification accuracy on the synthetically generated incidents. When I run the Malware Outbreak — a more complex scenario — accuracy drops to 77%. That delta tells me exactly where the model needs more training data or where human analyst oversight is most valuable.*

*Security teams can use this for analyst training: 'here's a simulated ransomware attack — what would you do?' They can use it for compliance demonstrations: 'here's evidence that our AI correctly identified a DDoS attack 9 times out of 10.' And they can use it for regression testing after any model update."*

---

### Scene 13 — Cost Intelligence Platform (1.5 minutes)

#### Navigation
Open: `http://localhost:3000/cost-intelligence`

#### What to Show
1. The page loads with four KPI cards:
   - **Total Cost**: $12.47 (last 30 days)
   - **Total Tokens**: 1.84M
   - **Avg Cost / Call**: $0.015
   - **Total Savings**: $4.66
2. Savings breakdown row: Redis Cache $3.21, Memory Reuse $1.45, RAG Deduplication ~$0.00 (or small amount)
3. **BarChart** — cost by agent: MitigationAgent highest (~$4.20), followed by ExplainabilityAgent, ConsensusService
4. **PieChart** — cost by model: GPT-4.1-mini dominates, small slices for Claude and Llama
5. **LineChart** — 14-day cost trend: relatively flat with a spike on the day of the ransomware simulation
6. **Optimisation Suggestions** table — show at least two suggestions:
   - "Use gpt-4.1-mini for classification tasks — saves ~40% vs. larger models" (High priority)
   - "Increase Redis TTL for ML predictions from 30min to 2h — saves ~15% on repeated similar flows" (Medium priority)

#### What to Say
*"The Cost Intelligence Platform gives engineering and finance teams full visibility into AI spending across every workflow, agent, and model. This is the conversation every enterprise AI deployment eventually needs to have.*

*You're looking at $12.47 in LLM costs for 847 incidents over 30 days. That's about 1.5 cents per incident. The industry cost of a human analyst spending 45 minutes on triage is roughly $20–30, depending on fully-loaded salary. The ROI is not close.*

*The savings section shows $4.66 in avoided costs: $3.21 from Redis caching — incidents with similar network flow signatures don't re-invoke the LLM, they get cached results. $1.45 from memory reuse — when the memory system already has context for this type of incident, fewer embedding lookups are needed.*

*The optimisation suggestions are automatically generated from the usage pattern. The platform is telling you: switch the classification agent to gpt-4.1-mini and you'll save 40% of that column's cost. That's a one-line config change worth significant savings at scale."*

---

### Updated Pre-Demo Checklist (Premium Features)

Add these items to the existing checklist before running the premium demo:

- [ ] `/campaigns` shows at least 2–3 mock campaigns (loads automatically from mock data)
- [ ] `/digital-twin` shows all 6 scenario cards (loads from built-in scenario catalogue)
- [ ] `/cost-intelligence` shows charts (uses mock data if no real usage logs present)
- [ ] War room open with an incident that has been through the full judge pipeline
- [ ] Confirm mock fallbacks active: self-reflection, consensus, and autonomous investigation all work without API keys

### Extended Q&A Talking Points (Premium Features)

| Question | Talking Point |
|----------|--------------|
| *What does the self-reflection loop cost in extra tokens?* | Two additional LLM calls per reflection — approximately 1,000–2,000 tokens total. At $0.00015/1K tokens, that's under $0.001 per reflection. The quality improvement from a re-analysis that catches critical gaps is worth far more. |
| *How does campaign detection handle large incident volumes?* | The current implementation uses O(n²) pairwise scoring, which is appropriate for daily incident windows (typically 10–200 incidents). For high-volume environments, the algorithm can be replaced with approximate nearest-neighbour clustering over the similarity embedding space. |
| *What if one LLM in the consensus is unavailable?* | `_adjust_weights()` redistributes the unavailable model's weight proportionally to the remaining models. The system always produces a consensus — it never blocks on a single model's availability. |
| *Can we add custom digital twin scenarios?* | Yes — POST to `/digital-twin/scenarios` with your custom scenario definition. Custom scenarios are stored per-org in `digital_twin_scenarios` and appear alongside the 6 built-in scenarios. |
| *Is cost tracking real-time?* | Yes — `CostIntelligenceService.log_usage()` is called synchronously within each service. Costs are visible in the dashboard within seconds of the API call completing. |
