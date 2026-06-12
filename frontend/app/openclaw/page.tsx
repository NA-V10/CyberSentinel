"use client";

import { useState } from "react";
import { Ticket, Bell, Send, ExternalLink, CheckCircle, AlertCircle, Loader2, ChevronDown, ChevronUp } from "lucide-react";
import api from "@/lib/api";

type Status = "idle" | "loading" | "success" | "error";

interface JiraResult {
  status: string;
  ticket_key?: string;
  ticket_url?: string;
  detail?: string;
}

interface NotifyResult {
  status: string;
  detail?: string;
}

interface DispatchResult {
  jira: JiraResult;
  notification: NotifyResult;
}

// ---------------------------------------------------------------------------
// Small reusable components
// ---------------------------------------------------------------------------

function SectionCard({ title, icon: Icon, children }: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-card border border-border rounded-xl p-6 shadow-[0_0_30px_rgba(0,212,255,0.04)]">
      <div className="flex items-center gap-2 mb-5">
        <div className="p-1.5 rounded-md bg-primary/10 border border-primary/20">
          <Icon className="w-4 h-4 text-primary" />
        </div>
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      </div>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}

function Input({ ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors"
    />
  );
}

function Textarea({ ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors resize-none"
    />
  );
}

function Select({ children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors"
    >
      {children}
    </select>
  );
}

function ResultBox({ result, label }: { result: JiraResult | NotifyResult | null; label: string }) {
  if (!result) return null;
  const isError = result.status === "error";
  const isSkipped = result.status === "skipped";

  return (
    <div className={`rounded-lg border p-4 text-sm ${
      isError
        ? "border-destructive/50 bg-destructive/5 text-destructive"
        : isSkipped
        ? "border-border bg-muted/30 text-muted-foreground"
        : "border-accent/50 bg-accent/5 text-accent"
    }`}>
      <div className="flex items-start gap-2">
        {isError ? (
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
        ) : (
          <CheckCircle className="w-4 h-4 mt-0.5 shrink-0" />
        )}
        <div className="space-y-1">
          <p className="font-medium">{label}</p>
          {"ticket_key" in result && result.ticket_key && (
            <p>
              Ticket:{" "}
              {"ticket_url" in result && result.ticket_url ? (
                <a
                  href={(result as JiraResult).ticket_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline underline-offset-2 inline-flex items-center gap-1"
                >
                  {result.ticket_key}
                  <ExternalLink className="w-3 h-3" />
                </a>
              ) : (
                result.ticket_key
              )}
            </p>
          )}
          {result.detail && <p className="text-xs opacity-80">{result.detail}</p>}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function OpenClawPage() {
  // --- Dispatch (combined) form ---
  const [summary, setSummary] = useState("");
  const [description, setDescription] = useState("");
  const [severity, setSeverity] = useState("medium");
  const [attackType, setAttackType] = useState("");
  const [incidentId, setIncidentId] = useState("");
  const [projectKey, setProjectKey] = useState("");
  const [escalationLevel, setEscalationLevel] = useState("L1");
  const [notifyEnabled, setNotifyEnabled] = useState(true);

  const [dispatchStatus, setDispatchStatus] = useState<Status>("idle");
  const [dispatchResult, setDispatchResult] = useState<DispatchResult | null>(null);

  // --- Standalone notify form ---
  const [notifySummary, setNotifySummary] = useState("");
  const [notifyIncidentId, setNotifyIncidentId] = useState("");
  const [notifySeverity, setNotifySeverity] = useState("medium");
  const [notifyThreatClass, setNotifyThreatClass] = useState("");
  const [notifyTicketUrl, setNotifyTicketUrl] = useState("");
  const [notifyStatus, setNotifyStatus] = useState<Status>("idle");
  const [notifyResult, setNotifyResult] = useState<NotifyResult | null>(null);

  const [showNotifyForm, setShowNotifyForm] = useState(false);

  // ---- handlers ----

  async function handleDispatch(e: React.FormEvent) {
    e.preventDefault();
    if (!summary.trim()) return;
    setDispatchStatus("loading");
    setDispatchResult(null);
    try {
      const { data } = await api.post<DispatchResult>(
        "/openclaw/dispatch",
        {
          summary: summary.trim(),
          description: description.trim() || summary.trim(),
          severity,
          attack_type: attackType || undefined,
          incident_id: incidentId || undefined,
          project_key: projectKey || undefined,
          escalation_level: escalationLevel || undefined,
          notify: notifyEnabled,
        }
      );
      setDispatchResult(data);
      setDispatchStatus("success");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Request failed";
      setDispatchResult({
        jira: { status: "error", detail },
        notification: { status: "skipped" },
      });
      setDispatchStatus("error");
    }
  }

  async function handleNotify(e: React.FormEvent) {
    e.preventDefault();
    if (!notifySummary.trim() || !notifyIncidentId.trim()) return;
    setNotifyStatus("loading");
    setNotifyResult(null);
    try {
      const { data } = await api.post<NotifyResult>(
        "/openclaw/notify",
        {
          incident_id: notifyIncidentId.trim(),
          summary: notifySummary.trim(),
          severity: notifySeverity,
          threat_class: notifyThreatClass || undefined,
          ticket_url: notifyTicketUrl || undefined,
        }
      );
      setNotifyResult(data);
      setNotifyStatus("success");
    } catch {
      setNotifyResult({ status: "error", detail: "Notification failed" });
      setNotifyStatus("error");
    }
  }

  // ---- render ----

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-1">
          <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
            <Ticket className="w-5 h-5 text-primary" />
          </div>
          <h1 className="text-xl font-bold text-foreground">
            OpenClaw <span className="text-primary">Integration</span>
          </h1>
        </div>
        <p className="text-sm text-muted-foreground ml-12">
          Create Jira tickets and send incident notifications via the OpenClaw agent layer.
        </p>
      </div>

      {/* Dispatch form — Jira + Notify combined */}
      <SectionCard title="Create Jira Ticket" icon={Ticket}>
        <form onSubmit={handleDispatch} className="space-y-4">
          <Field label="Summary *">
            <Input
              placeholder="e.g. Critical SQL injection attempt on /api/users"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              required
            />
          </Field>

          <Field label="Description">
            <Textarea
              rows={3}
              placeholder="Detailed incident description (optional — defaults to summary)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </Field>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Severity">
              <Select value={severity} onChange={(e) => setSeverity(e.target.value)}>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </Select>
            </Field>

            <Field label="Escalation Level">
              <Select value={escalationLevel} onChange={(e) => setEscalationLevel(e.target.value)}>
                <option value="L1">L1</option>
                <option value="L2">L2</option>
                <option value="L3">L3</option>
                <option value="SOC_Manager">SOC Manager</option>
              </Select>
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Attack Type">
              <Input
                placeholder="e.g. SQL Injection"
                value={attackType}
                onChange={(e) => setAttackType(e.target.value)}
              />
            </Field>

            <Field label="Jira Project Key">
              <Input
                placeholder="e.g. CS (defaults to env)"
                value={projectKey}
                onChange={(e) => setProjectKey(e.target.value)}
              />
            </Field>
          </div>

          <Field label="Incident ID (optional)">
            <Input
              placeholder="UUID from analysis (links ticket to incident record)"
              value={incidentId}
              onChange={(e) => setIncidentId(e.target.value)}
            />
          </Field>

          {/* Notify toggle */}
          <label className="flex items-center gap-2.5 cursor-pointer select-none">
            <div
              onClick={() => setNotifyEnabled((v) => !v)}
              className={`relative w-9 h-5 rounded-full transition-colors ${
                notifyEnabled ? "bg-primary" : "bg-muted border border-border"
              }`}
            >
              <div
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-background transition-transform ${
                  notifyEnabled ? "translate-x-4" : "translate-x-0.5"
                }`}
              />
            </div>
            <span className="text-sm text-muted-foreground">
              Also send webhook notification
            </span>
          </label>

          <button
            type="submit"
            disabled={dispatchStatus === "loading" || !summary.trim()}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-primary text-background text-sm font-medium hover:bg-primary/90 hover:shadow-[0_0_20px_rgba(0,212,255,0.3)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {dispatchStatus === "loading" ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            {dispatchStatus === "loading" ? "Dispatching…" : "Create Ticket"}
          </button>

          {/* Results */}
          {dispatchResult && (
            <div className="space-y-2 pt-1">
              <ResultBox
                result={dispatchResult.jira}
                label={
                  dispatchResult.jira.status === "created"
                    ? "Jira ticket created"
                    : "Jira ticket failed"
                }
              />
              {dispatchResult.notification && Object.keys(dispatchResult.notification).length > 0 && (
                <ResultBox
                  result={dispatchResult.notification}
                  label={
                    dispatchResult.notification.status === "sent"
                      ? "Notification delivered"
                      : dispatchResult.notification.status === "skipped"
                      ? "Notification skipped (no webhook configured)"
                      : "Notification failed"
                  }
                />
              )}
            </div>
          )}
        </form>
      </SectionCard>

      {/* Standalone notify form (collapsible) */}
      <div className="bg-card border border-border rounded-xl overflow-hidden shadow-[0_0_30px_rgba(0,212,255,0.04)]">
        <button
          type="button"
          onClick={() => setShowNotifyForm((v) => !v)}
          className="w-full flex items-center justify-between px-6 py-4 hover:bg-muted/20 transition-colors"
        >
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-secondary/10 border border-secondary/20">
              <Bell className="w-4 h-4 text-secondary" />
            </div>
            <span className="text-sm font-semibold text-foreground">
              Send Standalone Notification
            </span>
          </div>
          {showNotifyForm ? (
            <ChevronUp className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          )}
        </button>

        {showNotifyForm && (
          <form onSubmit={handleNotify} className="px-6 pb-6 space-y-4">
            <div className="h-px bg-border mb-2" />

            <Field label="Incident ID *">
              <Input
                placeholder="UUID of the incident"
                value={notifyIncidentId}
                onChange={(e) => setNotifyIncidentId(e.target.value)}
                required
              />
            </Field>

            <Field label="Summary *">
              <Input
                placeholder="Brief description of the incident"
                value={notifySummary}
                onChange={(e) => setNotifySummary(e.target.value)}
                required
              />
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Severity">
                <Select
                  value={notifySeverity}
                  onChange={(e) => setNotifySeverity(e.target.value)}
                >
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </Select>
              </Field>

              <Field label="Attack Type">
                <Input
                  placeholder="e.g. Ransomware"
                  value={notifyThreatClass}
                  onChange={(e) => setNotifyThreatClass(e.target.value)}
                />
              </Field>
            </div>

            <Field label="Jira Ticket URL (optional)">
              <Input
                placeholder="https://yourcompany.atlassian.net/browse/CS-42"
                value={notifyTicketUrl}
                onChange={(e) => setNotifyTicketUrl(e.target.value)}
              />
            </Field>

            <button
              type="submit"
              disabled={
                notifyStatus === "loading" ||
                !notifySummary.trim() ||
                !notifyIncidentId.trim()
              }
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-secondary/20 border border-secondary/40 text-secondary text-sm font-medium hover:bg-secondary/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {notifyStatus === "loading" ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Bell className="w-4 h-4" />
              )}
              {notifyStatus === "loading" ? "Sending…" : "Send Notification"}
            </button>

            {notifyResult && (
              <ResultBox
                result={notifyResult}
                label={
                  notifyResult.status === "sent"
                    ? "Notification delivered"
                    : notifyResult.status === "skipped"
                    ? "Skipped (no webhook URL configured)"
                    : "Notification failed"
                }
              />
            )}
          </form>
        )}
      </div>

      {/* Config hint */}
      <div className="rounded-lg border border-border bg-muted/20 p-4 text-xs text-muted-foreground space-y-1">
        <p className="font-medium text-foreground text-xs">Required environment variables</p>
        <p><code className="text-primary">JIRA_BASE_URL</code> — e.g. https://yourcompany.atlassian.net</p>
        <p><code className="text-primary">JIRA_EMAIL</code> — your Atlassian account email</p>
        <p><code className="text-primary">JIRA_API_TOKEN</code> — from id.atlassian.com/manage-profile/security/api-tokens</p>
        <p><code className="text-primary">JIRA_PROJECT_KEY</code> — default project key (e.g. CS)</p>
        <p><code className="text-primary">OPENCLAW_WEBHOOK_URL</code> — Slack-compatible webhook for notifications</p>
        <p><code className="text-primary">OPENCLAW_API_KEY</code> — optional, routes via OpenClaw gateway when set</p>
      </div>
    </div>
  );
}
