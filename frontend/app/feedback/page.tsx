"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare,
  Star,
  CheckSquare,
  Square,
  Send,
  TrendingUp,
  ThumbsUp,
  BarChart2,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { SeverityBadge, ThreatClassBadge } from "@/components/incidents/SeverityBadge";
import { formatRelativeTime } from "@/lib/utils";
import { toast } from "sonner";

interface FeedbackItem {
  id: string;
  incident_id: string;
  title: string;
  threat_class: string;
  severity: "critical" | "high" | "medium" | "low";
  analyzed_at: string;
  rating: number | null;
  comment: string;
  mitigation_worked: boolean | null;
}

const MOCK_INCIDENTS: FeedbackItem[] = [
  {
    id: "FB-001",
    incident_id: "INC-001",
    title: "Ransomware Attack on Finance",
    threat_class: "Ransomware",
    severity: "critical",
    analyzed_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    rating: 5,
    comment: "Excellent analysis. Mitigation steps were spot on.",
    mitigation_worked: true,
  },
  {
    id: "FB-002",
    incident_id: "INC-002",
    title: "SSH Brute Force Attack",
    threat_class: "Brute Force",
    severity: "high",
    analyzed_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    rating: 4,
    comment: "Good recommendations but could be more specific.",
    mitigation_worked: true,
  },
  {
    id: "FB-003",
    incident_id: "INC-003",
    title: "SQL Injection Attempt",
    threat_class: "SQL Injection",
    severity: "medium",
    analyzed_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    rating: null,
    comment: "",
    mitigation_worked: null,
  },
  {
    id: "FB-004",
    incident_id: "INC-004",
    title: "Phishing Campaign",
    threat_class: "Phishing",
    severity: "high",
    analyzed_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    rating: 3,
    comment: "Analysis was helpful but missed some indicators.",
    mitigation_worked: false,
  },
  {
    id: "FB-005",
    incident_id: "INC-005",
    title: "DDoS Attack on Public API",
    threat_class: "DDoS",
    severity: "critical",
    analyzed_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    rating: null,
    comment: "",
    mitigation_worked: null,
  },
];

const feedbackTrendData = [
  { week: "Week 1", avg_rating: 3.8 },
  { week: "Week 2", avg_rating: 4.1 },
  { week: "Week 3", avg_rating: 3.9 },
  { week: "Week 4", avg_rating: 4.4 },
  { week: "Week 5", avg_rating: 4.2 },
  { week: "Week 6", avg_rating: 4.6 },
];

function StarRating({
  value,
  onChange,
  disabled = false,
}: {
  value: number;
  onChange: (v: number) => void;
  disabled?: boolean;
}) {
  const [hovered, setHovered] = useState(0);

  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          onClick={() => !disabled && onChange(star)}
          onMouseEnter={() => !disabled && setHovered(star)}
          onMouseLeave={() => !disabled && setHovered(0)}
          disabled={disabled}
          className="p-0.5 disabled:cursor-default"
        >
          <Star
            className={`w-5 h-5 transition-colors ${
              star <= (hovered || value)
                ? "fill-yellow-400 text-yellow-400"
                : "text-muted-foreground"
            }`}
          />
        </button>
      ))}
    </div>
  );
}

interface FeedbackFormState {
  rating: number;
  comment: string;
  mitigation_worked: boolean;
}

export default function FeedbackPage() {
  const [incidents, setIncidents] = useState<FeedbackItem[]>(MOCK_INCIDENTS);
  const [selectedIncident, setSelectedIncident] = useState<string | null>(null);
  const [form, setForm] = useState<FeedbackFormState>({
    rating: 0,
    comment: "",
    mitigation_worked: true,
  });
  const [submitting, setSubmitting] = useState(false);

  // Stats
  const ratedIncidents = incidents.filter((i) => i.rating !== null);
  const avgRating =
    ratedIncidents.length > 0
      ? ratedIncidents.reduce((sum, i) => sum + (i.rating || 0), 0) /
        ratedIncidents.length
      : 0;
  const mitigationSuccessRate =
    ratedIncidents.filter((i) => i.mitigation_worked === true).length /
    Math.max(ratedIncidents.length, 1);
  const pendingFeedback = incidents.filter((i) => i.rating === null).length;

  const handleOpenFeedback = (incidentId: string) => {
    const incident = incidents.find((i) => i.id === incidentId);
    if (incident && incident.rating !== null) {
      setForm({
        rating: incident.rating || 0,
        comment: incident.comment || "",
        mitigation_worked: incident.mitigation_worked ?? true,
      });
    } else {
      setForm({ rating: 0, comment: "", mitigation_worked: true });
    }
    setSelectedIncident(incidentId === selectedIncident ? null : incidentId);
  };

  const handleSubmitFeedback = async (incidentId: string) => {
    if (form.rating === 0) {
      toast.error("Please select a rating");
      return;
    }

    setSubmitting(true);
    await new Promise((r) => setTimeout(r, 800));

    setIncidents((prev) =>
      prev.map((item) =>
        item.id === incidentId
          ? {
              ...item,
              rating: form.rating,
              comment: form.comment,
              mitigation_worked: form.mitigation_worked,
            }
          : item
      )
    );

    setSelectedIncident(null);
    setSubmitting(false);
    toast.success("Feedback submitted! Thank you.");
  };

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground">Feedback</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Rate AI analyses and help improve the system
        </p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="cyber-card p-5 border border-border"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
              <Star className="w-5 h-5 text-yellow-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-foreground">
                {avgRating.toFixed(1)}
                <span className="text-base text-muted-foreground font-normal">
                  /5
                </span>
              </div>
              <div className="text-xs text-muted-foreground">Average Rating</div>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="cyber-card p-5 border border-border"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-500/10 border border-green-500/20">
              <ThumbsUp className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-foreground">
                {Math.round(mitigationSuccessRate * 100)}%
              </div>
              <div className="text-xs text-muted-foreground">
                Mitigation Success Rate
              </div>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="cyber-card p-5 border border-border"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
              <MessageSquare className="w-5 h-5 text-primary" />
            </div>
            <div>
              <div className="text-2xl font-bold text-foreground">
                {pendingFeedback}
              </div>
              <div className="text-xs text-muted-foreground">
                Pending Feedback
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Incidents Table */}
        <div className="xl:col-span-2 space-y-3">
          <h2 className="text-sm font-semibold text-foreground mb-4">
            Analyzed Incidents
          </h2>

          {incidents.map((incident, i) => (
            <motion.div
              key={incident.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="cyber-card border border-border overflow-hidden"
            >
              {/* Incident Row */}
              <div className="flex items-start gap-3 p-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-xs font-mono text-muted-foreground">
                      {incident.incident_id}
                    </span>
                    <SeverityBadge severity={incident.severity} size="sm" />
                    <ThreatClassBadge threatClass={incident.threat_class} />
                  </div>
                  <p className="text-sm font-medium text-foreground">
                    {incident.title}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {formatRelativeTime(incident.analyzed_at)}
                  </p>
                </div>

                {/* Rating Display or Add Feedback button */}
                <div className="shrink-0 text-right">
                  {incident.rating !== null ? (
                    <div>
                      <div className="flex justify-end">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <Star
                            key={star}
                            className={`w-4 h-4 ${
                              star <= incident.rating!
                                ? "fill-yellow-400 text-yellow-400"
                                : "text-muted-foreground"
                            }`}
                          />
                        ))}
                      </div>
                      <button
                        onClick={() => handleOpenFeedback(incident.id)}
                        className="text-xs text-primary hover:underline mt-1"
                      >
                        Edit
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => handleOpenFeedback(incident.id)}
                      className="px-3 py-1.5 text-xs bg-primary/10 border border-primary/30 rounded-md text-primary hover:bg-primary/20 transition-colors"
                    >
                      Rate
                    </button>
                  )}
                </div>
              </div>

              {/* Comment preview */}
              {incident.comment && (
                <div className="px-4 pb-3">
                  <p className="text-xs text-muted-foreground italic">
                    "{incident.comment}"
                  </p>
                  {incident.mitigation_worked !== null && (
                    <span
                      className={`text-xs mt-1 inline-block ${
                        incident.mitigation_worked
                          ? "text-green-400"
                          : "text-red-400"
                      }`}
                    >
                      Mitigation:{" "}
                      {incident.mitigation_worked ? "worked" : "did not work"}
                    </span>
                  )}
                </div>
              )}

              {/* Feedback Form */}
              <AnimatePresence>
                {selectedIncident === incident.id && (
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: "auto" }}
                    exit={{ height: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="p-4 border-t border-border bg-muted/10 space-y-4">
                      <h4 className="text-xs font-semibold text-foreground uppercase tracking-wide">
                        Submit Feedback
                      </h4>

                      {/* Rating */}
                      <div>
                        <label className="text-xs text-muted-foreground block mb-2">
                          Rating *
                        </label>
                        <StarRating
                          value={form.rating}
                          onChange={(v) =>
                            setForm((prev) => ({ ...prev, rating: v }))
                          }
                        />
                      </div>

                      {/* Mitigation checkbox */}
                      <button
                        onClick={() =>
                          setForm((prev) => ({
                            ...prev,
                            mitigation_worked: !prev.mitigation_worked,
                          }))
                        }
                        className="flex items-center gap-2 text-sm text-foreground group"
                      >
                        {form.mitigation_worked ? (
                          <CheckSquare className="w-4 h-4 text-primary" />
                        ) : (
                          <Square className="w-4 h-4 text-muted-foreground group-hover:text-foreground" />
                        )}
                        <span>Mitigation steps worked effectively</span>
                      </button>

                      {/* Comment */}
                      <div>
                        <label className="text-xs text-muted-foreground block mb-1">
                          Comment (optional)
                        </label>
                        <textarea
                          value={form.comment}
                          onChange={(e) =>
                            setForm((prev) => ({
                              ...prev,
                              comment: e.target.value,
                            }))
                          }
                          placeholder="How accurate was the analysis? Any improvements?"
                          rows={3}
                          className="w-full cyber-input text-sm resize-none"
                        />
                      </div>

                      {/* Submit */}
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => handleSubmitFeedback(incident.id)}
                          disabled={submitting || form.rating === 0}
                          className="flex items-center gap-2 px-4 py-2 bg-primary text-background rounded-lg text-sm font-semibold hover:bg-primary/90 transition-all disabled:opacity-50"
                        >
                          <Send className="w-4 h-4" />
                          {submitting ? "Submitting..." : "Submit Feedback"}
                        </button>
                        <button
                          onClick={() => setSelectedIncident(null)}
                          className="px-4 py-2 border border-border rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>

        {/* Sidebar: Stats */}
        <div className="space-y-4">
          {/* Rating Trend Chart */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="cyber-card p-5 border border-border"
          >
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold text-foreground">
                Rating Trend
              </h3>
            </div>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={feedbackTrendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis
                  dataKey="week"
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  axisLine={{ stroke: "#1f2937" }}
                />
                <YAxis
                  domain={[0, 5]}
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  axisLine={{ stroke: "#1f2937" }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#111827",
                    border: "1px solid #1f2937",
                    borderRadius: "6px",
                    fontSize: 11,
                    color: "#e2e8f0",
                  }}
                />
                <Bar dataKey="avg_rating" fill="#00d4ff" radius={[4, 4, 0, 0]} name="Avg Rating" />
              </BarChart>
            </ResponsiveContainer>
          </motion.div>

          {/* Top Attack Types by Frequency */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="cyber-card p-5 border border-border"
          >
            <div className="flex items-center gap-2 mb-4">
              <BarChart2 className="w-4 h-4 text-secondary" />
              <h3 className="text-sm font-semibold text-foreground">
                Common Attack Types
              </h3>
            </div>
            <div className="space-y-3">
              {[
                { type: "Ransomware", count: 3, pct: 30 },
                { type: "Phishing", count: 3, pct: 30 },
                { type: "Brute Force", count: 2, pct: 20 },
                { type: "DDoS", count: 1, pct: 10 },
                { type: "SQL Injection", count: 1, pct: 10 },
              ].map((item) => (
                <div key={item.type}>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-muted-foreground">{item.type}</span>
                    <span className="text-foreground font-medium">
                      {item.count}
                    </span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                    <motion.div
                      className="h-full bg-secondary rounded-full"
                      initial={{ width: "0%" }}
                      animate={{ width: `${item.pct}%` }}
                      transition={{ duration: 0.6 }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Quick Stats */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="cyber-card p-5 border border-border"
          >
            <h3 className="text-sm font-semibold text-foreground mb-4">
              Summary
            </h3>
            <div className="space-y-3 text-sm">
              {[
                {
                  label: "Total Analyses",
                  value: incidents.length,
                  color: "text-primary",
                },
                {
                  label: "With Feedback",
                  value: ratedIncidents.length,
                  color: "text-green-400",
                },
                {
                  label: "Pending Rating",
                  value: pendingFeedback,
                  color: "text-yellow-400",
                },
                {
                  label: "Mitigation Worked",
                  value: `${Math.round(mitigationSuccessRate * 100)}%`,
                  color: "text-accent",
                },
              ].map((item) => (
                <div
                  key={item.label}
                  className="flex items-center justify-between"
                >
                  <span className="text-muted-foreground text-xs">
                    {item.label}
                  </span>
                  <span className={`font-semibold ${item.color}`}>
                    {item.value}
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </DashboardLayout>
  );
}
