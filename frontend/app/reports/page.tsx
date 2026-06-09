"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  FileText,
  Download,
  Calendar,
  Filter,
  Search,
  Eye,
  ChevronLeft,
  ChevronRight,
  X,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { SeverityBadge, ThreatClassBadge, EscalationBadge } from "@/components/incidents/SeverityBadge";
import { formatDate, formatRelativeTime } from "@/lib/utils";
import { toast } from "sonner";

interface Report {
  id: string;
  incident_id: string;
  title: string;
  summary: string;
  threat_class: string;
  severity: "critical" | "high" | "medium" | "low";
  escalation_level: "P1" | "P2" | "P3" | "P4";
  judge_score: number;
  analysis_time_seconds: number;
  created_at: string;
  source_ip?: string;
  protocol?: string;
}

const MOCK_REPORTS: Report[] = [
  {
    id: "RPT-001",
    incident_id: "INC-001",
    title: "Ransomware Attack on Finance Department",
    summary: "Critical ransomware infection detected across finance workstations. Files encrypted with .locked extension. Attack vector identified as phishing email. Immediate isolation required.",
    threat_class: "Ransomware",
    severity: "critical",
    escalation_level: "P1",
    judge_score: 9.2,
    analysis_time_seconds: 1.8,
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    source_ip: "192.168.10.45",
    protocol: "SMB",
  },
  {
    id: "RPT-002",
    incident_id: "INC-002",
    title: "SSH Brute Force Attack on Jump Server",
    summary: "Sustained SSH brute force attack from external IP targeting jump server. 5,000+ failed authentication attempts. IP blocklist recommended.",
    threat_class: "Brute Force",
    severity: "high",
    escalation_level: "P2",
    judge_score: 8.7,
    analysis_time_seconds: 1.4,
    created_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    source_ip: "45.33.32.156",
    protocol: "SSH",
  },
  {
    id: "RPT-003",
    incident_id: "INC-003",
    title: "SQL Injection Attempt on Customer Portal",
    summary: "SQL injection attack detected on /api/users endpoint. Malicious payload blocked by WAF. Database integrity confirmed intact.",
    threat_class: "SQL Injection",
    severity: "medium",
    escalation_level: "P3",
    judge_score: 8.1,
    analysis_time_seconds: 1.2,
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    source_ip: "203.0.113.100",
    protocol: "HTTP",
  },
  {
    id: "RPT-004",
    incident_id: "INC-004",
    title: "Phishing Campaign Targeting HR",
    summary: "Coordinated spear-phishing campaign targeting HR department. 3 employees clicked malicious links. Credentials potentially compromised. Password resets initiated.",
    threat_class: "Phishing",
    severity: "high",
    escalation_level: "P2",
    judge_score: 8.9,
    analysis_time_seconds: 1.6,
    created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    protocol: "SMTP",
  },
  {
    id: "RPT-005",
    incident_id: "INC-005",
    title: "DDoS Attack on Public API",
    summary: "Volumetric DDoS attack targeting public API endpoints. Peak traffic of 50,000 requests/second. CDN rate limiting engaged. Service degraded for 12 minutes.",
    threat_class: "DDoS",
    severity: "critical",
    escalation_level: "P1",
    judge_score: 9.0,
    analysis_time_seconds: 1.9,
    created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    protocol: "TCP",
  },
  {
    id: "RPT-006",
    incident_id: "INC-006",
    title: "Unauthorized Admin Access Detected",
    summary: "Privileged account accessed outside business hours from unusual geographic location. Session terminated. Multi-factor authentication enforcement recommended.",
    threat_class: "Insider Threat",
    severity: "high",
    escalation_level: "P2",
    judge_score: 7.8,
    analysis_time_seconds: 1.5,
    created_at: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(),
    protocol: "HTTPS",
  },
];

export default function ReportsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [dateFilter, setDateFilter] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [exportingId, setExportingId] = useState<string | null>(null);

  const ITEMS_PER_PAGE = 5;

  const filteredReports = MOCK_REPORTS.filter((report) => {
    const matchesSearch =
      !searchQuery ||
      report.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      report.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
      report.threat_class.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesSeverity = !severityFilter || report.severity === severityFilter;

    let matchesDate = true;
    if (dateFilter) {
      const now = new Date();
      const reportDate = new Date(report.created_at);
      const diffDays =
        (now.getTime() - reportDate.getTime()) / (1000 * 60 * 60 * 24);
      if (dateFilter === "today") matchesDate = diffDays < 1;
      else if (dateFilter === "week") matchesDate = diffDays < 7;
      else if (dateFilter === "month") matchesDate = diffDays < 30;
    }

    return matchesSearch && matchesSeverity && matchesDate;
  });

  const totalPages = Math.ceil(filteredReports.length / ITEMS_PER_PAGE);
  const paginatedReports = filteredReports.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  const handleExportPDF = async (report: Report) => {
    setExportingId(report.id);

    // Simulate PDF generation
    await new Promise((r) => setTimeout(r, 1500));

    // Create a text-based export (real implementation would use a PDF library)
    const content = `
CYBERSENTINEL AI - INCIDENT REPORT
===================================
Report ID: ${report.id}
Incident ID: ${report.incident_id}
Date: ${formatDate(report.created_at)}

CLASSIFICATION
--------------
Threat Class: ${report.threat_class}
Severity: ${report.severity.toUpperCase()}
Escalation Level: ${report.escalation_level}
Quality Score: ${report.judge_score}/10

TITLE
-----
${report.title}

SUMMARY
-------
${report.summary}

METADATA
--------
Source IP: ${report.source_ip || "N/A"}
Protocol: ${report.protocol || "N/A"}
Analysis Time: ${report.analysis_time_seconds}s

Generated by CyberSentinel AI
    `.trim();

    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${report.id}-report.txt`;
    a.click();
    URL.revokeObjectURL(url);

    setExportingId(null);
    toast.success(`Report ${report.id} exported`);
  };

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Reports</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Generated incident analysis reports
          </p>
        </div>
        <div className="text-sm text-muted-foreground">
          {filteredReports.length} reports
        </div>
      </div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="cyber-card p-4 border border-border mb-6"
      >
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="relative flex-1 min-w-48">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Search reports..."
              className="w-full cyber-input pl-9"
            />
          </div>

          {/* Severity filter */}
          <select
            value={severityFilter}
            onChange={(e) => {
              setSeverityFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="cyber-input min-w-32"
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          {/* Date filter */}
          <select
            value={dateFilter}
            onChange={(e) => {
              setDateFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="cyber-input min-w-32"
          >
            <option value="">All Time</option>
            <option value="today">Today</option>
            <option value="week">This Week</option>
            <option value="month">This Month</option>
          </select>

          {/* Clear filters */}
          {(searchQuery || severityFilter || dateFilter) && (
            <button
              onClick={() => {
                setSearchQuery("");
                setSeverityFilter("");
                setDateFilter("");
                setCurrentPage(1);
              }}
              className="flex items-center gap-1.5 px-3 py-2 text-xs text-muted-foreground hover:text-foreground border border-border rounded-md hover:bg-muted transition-colors"
            >
              <X className="w-3.5 h-3.5" />
              Clear
            </button>
          )}
        </div>
      </motion.div>

      {/* Reports List */}
      <div className="space-y-4">
        {paginatedReports.map((report, i) => (
          <motion.div
            key={report.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: i * 0.05 }}
            className="cyber-card border border-border hover:border-primary/30 transition-all duration-200 overflow-hidden"
          >
            {/* Report Header */}
            <div className="flex items-start gap-4 p-5">
              <div className="p-2.5 rounded-lg bg-primary/10 border border-primary/20 shrink-0">
                <FileText className="w-5 h-5 text-primary" />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className="text-xs font-mono text-muted-foreground">
                        {report.id}
                      </span>
                      <span className="text-xs text-muted-foreground">·</span>
                      <span className="text-xs text-muted-foreground">
                        {formatRelativeTime(report.created_at)}
                      </span>
                    </div>
                    <h3 className="text-sm font-semibold text-foreground mb-2">
                      {report.title}
                    </h3>
                    <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                      {report.summary}
                    </p>
                  </div>

                  <div className="flex flex-col items-end gap-2 shrink-0">
                    <div className="text-lg font-bold text-primary">
                      {report.judge_score}
                      <span className="text-xs text-muted-foreground font-normal">
                        /10
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      quality score
                    </div>
                  </div>
                </div>

                {/* Badges row */}
                <div className="flex items-center gap-2 flex-wrap mt-3">
                  <SeverityBadge severity={report.severity} size="sm" />
                  <ThreatClassBadge
                    threatClass={report.threat_class}
                    className="text-xs"
                  />
                  <EscalationBadge level={report.escalation_level} />
                  {report.source_ip && (
                    <span className="text-xs font-mono text-muted-foreground border border-border px-2 py-0.5 rounded">
                      {report.source_ip}
                    </span>
                  )}
                  {report.protocol && (
                    <span className="text-xs font-mono text-muted-foreground border border-border px-2 py-0.5 rounded">
                      {report.protocol}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Report Footer */}
            <div className="flex items-center justify-between px-5 py-3 border-t border-border bg-muted/20">
              <div className="text-xs text-muted-foreground">
                Generated {formatDate(report.created_at)} ·{" "}
                <span className="font-mono text-primary">
                  {report.analysis_time_seconds}s
                </span>{" "}
                analysis time
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() =>
                    setSelectedReport(
                      selectedReport?.id === report.id ? null : report
                    )
                  }
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                >
                  <Eye className="w-3.5 h-3.5" />
                  {selectedReport?.id === report.id ? "Hide" : "Preview"}
                </button>
                <button
                  onClick={() => handleExportPDF(report)}
                  disabled={exportingId === report.id}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-primary/10 border border-primary/30 rounded-md text-primary hover:bg-primary/20 transition-colors disabled:opacity-50"
                >
                  <Download
                    className={`w-3.5 h-3.5 ${
                      exportingId === report.id ? "animate-bounce" : ""
                    }`}
                  />
                  {exportingId === report.id ? "Exporting..." : "Export"}
                </button>
              </div>
            </div>

            {/* Preview Expanded */}
            {selectedReport?.id === report.id && (
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: "auto" }}
                exit={{ height: 0 }}
                className="border-t border-border overflow-hidden"
              >
                <div className="p-5 bg-muted/10">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
                    Full Summary
                  </h4>
                  <p className="text-sm text-foreground leading-relaxed">
                    {report.summary}
                  </p>

                  <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {[
                      { label: "Incident ID", value: report.incident_id },
                      { label: "Report ID", value: report.id },
                      { label: "Source IP", value: report.source_ip || "N/A" },
                      { label: "Protocol", value: report.protocol || "N/A" },
                    ].map((item) => (
                      <div key={item.label} className="bg-muted rounded-lg p-3">
                        <p className="text-xs text-muted-foreground mb-1">
                          {item.label}
                        </p>
                        <p className="text-sm text-foreground font-mono">
                          {item.value}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </motion.div>
        ))}
      </div>

      {/* Empty state */}
      {filteredReports.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <FileText className="w-12 h-12 text-muted-foreground/30 mb-4" />
          <p className="text-sm text-muted-foreground">No reports found</p>
          <p className="text-xs text-muted-foreground mt-1">
            Try adjusting your filters
          </p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-6">
          <p className="text-xs text-muted-foreground">
            Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1}–
            {Math.min(currentPage * ITEMS_PER_PAGE, filteredReports.length)} of{" "}
            {filteredReports.length}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-2 rounded-md border border-border hover:bg-muted text-muted-foreground disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                onClick={() => setCurrentPage(page)}
                className={`w-8 h-8 rounded-md text-sm font-medium transition-colors ${
                  currentPage === page
                    ? "bg-primary text-background"
                    : "border border-border text-muted-foreground hover:bg-muted"
                }`}
              >
                {page}
              </button>
            ))}
            <button
              onClick={() =>
                setCurrentPage((p) => Math.min(totalPages, p + 1))
              }
              disabled={currentPage === totalPages}
              className="p-2 rounded-md border border-border hover:bg-muted text-muted-foreground disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
