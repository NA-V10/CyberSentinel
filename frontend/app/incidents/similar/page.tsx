"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Search, ArrowRight, Filter, X } from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { SeverityBadge, ThreatClassBadge } from "@/components/incidents/SeverityBadge";
import { formatRelativeTime } from "@/lib/utils";

interface SimilarIncident {
  id: string;
  title: string;
  description: string;
  threat_class: string;
  severity: "critical" | "high" | "medium" | "low";
  similarity_score: number;
  created_at: string;
  source_ip?: string;
  protocol?: string;
  mitigation_summary?: string;
}

const SAMPLE_RESULTS: SimilarIncident[] = [
  {
    id: "INC-2024-001",
    title: "Ryuk Ransomware on Windows Finance Servers",
    description: "Ryuk ransomware deployed across finance department Windows servers via lateral movement from initial phishing compromise. Files encrypted with .RYK extension.",
    threat_class: "Ransomware",
    severity: "critical",
    similarity_score: 0.94,
    created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    source_ip: "10.0.5.23",
    protocol: "SMB",
    mitigation_summary: "Isolated affected systems, restored from offline backup, patched SMB vulnerability",
  },
  {
    id: "INC-2024-015",
    title: "LockBit 3.0 Deployment via RDP",
    description: "LockBit ransomware deployed after successful RDP brute force. Attacker moved laterally across network before deploying payload at 2AM.",
    threat_class: "Ransomware",
    severity: "critical",
    similarity_score: 0.87,
    created_at: new Date(Date.now() - 12 * 24 * 60 * 60 * 1000).toISOString(),
    source_ip: "172.16.0.45",
    protocol: "RDP",
    mitigation_summary: "Disabled RDP access, deployed EDR solution, implemented network segmentation",
  },
  {
    id: "INC-2023-089",
    title: "BlackCat ALPHV Ransomware Campaign",
    description: "BlackCat ransomware targeting healthcare data. Exfiltrated patient data before encryption. Triple extortion threat.",
    threat_class: "Ransomware",
    severity: "critical",
    similarity_score: 0.82,
    created_at: new Date(Date.now() - 45 * 24 * 60 * 60 * 1000).toISOString(),
    protocol: "HTTPS",
    mitigation_summary: "Engaged DFIR team, notified regulators, negotiation avoided via backup recovery",
  },
  {
    id: "INC-2024-023",
    title: "Emotet Loader → Ransomware Chain",
    description: "Emotet malware loaded via macro-enabled document. Used as initial access for subsequent ransomware deployment.",
    threat_class: "Ransomware",
    severity: "high",
    similarity_score: 0.76,
    created_at: new Date(Date.now() - 20 * 24 * 60 * 60 * 1000).toISOString(),
    protocol: "SMTP",
    mitigation_summary: "Email filtering enhanced, macro execution blocked, affected accounts reset",
  },
];

export default function SimilarIncidentsPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SimilarIncident[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [severityFilter, setSeverityFilter] = useState("");
  const [minScore, setMinScore] = useState(0);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setIsSearching(true);
    setHasSearched(false);

    // Simulate API call
    await new Promise((r) => setTimeout(r, 1200));

    const filtered = SAMPLE_RESULTS.filter(
      (r) =>
        (!severityFilter || r.severity === severityFilter) &&
        r.similarity_score >= minScore / 100
    );
    setResults(filtered);
    setIsSearching(false);
    setHasSearched(true);
  };

  return (
    <DashboardLayout>
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground">
            Similar Incidents
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Semantic search across historical incidents using RAG
          </p>
        </div>

        {/* Search Form */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="cyber-card p-5 border border-border mb-6"
        >
          <div className="space-y-4">
            <div>
              <label className="text-xs text-muted-foreground mb-2 block">
                Describe the incident to find similar cases
              </label>
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. Ransomware detected on Windows servers with encrypted files..."
                rows={3}
                className="w-full cyber-input text-sm resize-none"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && e.ctrlKey) handleSearch();
                }}
              />
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="cyber-input text-sm min-w-36"
              >
                <option value="">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>

              <div className="flex items-center gap-2">
                <label className="text-xs text-muted-foreground">
                  Min similarity:
                </label>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={minScore}
                  onChange={(e) => setMinScore(Number(e.target.value))}
                  className="w-24 accent-primary"
                />
                <span className="text-xs font-mono text-primary w-8">
                  {minScore}%
                </span>
              </div>

              {(severityFilter || minScore > 0) && (
                <button
                  onClick={() => {
                    setSeverityFilter("");
                    setMinScore(0);
                  }}
                  className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                >
                  <X className="w-3.5 h-3.5" />
                  Clear
                </button>
              )}

              <button
                onClick={handleSearch}
                disabled={!query.trim() || isSearching}
                className="ml-auto flex items-center gap-2 px-5 py-2.5 bg-primary text-background rounded-lg text-sm font-semibold hover:bg-primary/90 transition-all disabled:opacity-50 hover:shadow-[0_0_20px_rgba(0,212,255,0.3)]"
              >
                <Search className="w-4 h-4" />
                {isSearching ? "Searching..." : "Search Similar"}
              </button>
            </div>
          </div>
        </motion.div>

        {/* Results */}
        {isSearching && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">
                Searching incident database...
              </p>
            </div>
          </div>
        )}

        {hasSearched && !isSearching && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Found{" "}
                <span className="text-foreground font-medium">
                  {results.length}
                </span>{" "}
                similar incidents
              </p>
            </div>

            {results.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Search className="w-10 h-10 text-muted-foreground/30 mb-3" />
                <p className="text-sm text-muted-foreground">
                  No similar incidents found
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Try a different description or relax filters
                </p>
              </div>
            ) : (
              results.map((incident, i) => (
                <motion.div
                  key={incident.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.08 }}
                  className="cyber-card border border-border hover:border-primary/30 transition-all duration-200"
                >
                  <div className="p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2 flex-wrap">
                          <span className="text-xs font-mono text-muted-foreground">
                            {incident.id}
                          </span>
                          <SeverityBadge severity={incident.severity} size="sm" />
                          <ThreatClassBadge threatClass={incident.threat_class} />
                          {incident.protocol && (
                            <span className="text-xs font-mono text-muted-foreground border border-border px-2 py-0.5 rounded">
                              {incident.protocol}
                            </span>
                          )}
                        </div>
                        <h3 className="text-sm font-semibold text-foreground mb-2">
                          {incident.title}
                        </h3>
                        <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                          {incident.description}
                        </p>

                        {incident.mitigation_summary && (
                          <div className="mt-3 p-3 bg-muted rounded-lg border border-border">
                            <p className="text-xs text-muted-foreground mb-1 font-medium">
                              Applied Mitigation
                            </p>
                            <p className="text-xs text-foreground">
                              {incident.mitigation_summary}
                            </p>
                          </div>
                        )}
                      </div>

                      <div className="shrink-0 text-right">
                        <div className="text-2xl font-black text-primary">
                          {Math.round(incident.similarity_score * 100)}%
                        </div>
                        <div className="text-xs text-muted-foreground">
                          similarity
                        </div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          {formatRelativeTime(incident.created_at)}
                        </div>
                      </div>
                    </div>

                    {/* Similarity bar */}
                    <div className="mt-3 bg-muted rounded-full h-1.5 overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-primary to-secondary rounded-full"
                        initial={{ width: "0%" }}
                        animate={{
                          width: `${incident.similarity_score * 100}%`,
                        }}
                        transition={{ duration: 0.6, delay: i * 0.08 + 0.2 }}
                      />
                    </div>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        )}

        {/* Initial state */}
        {!hasSearched && !isSearching && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="p-4 rounded-full bg-primary/10 border border-primary/20 mb-4">
              <Search className="w-8 h-8 text-primary" />
            </div>
            <h3 className="text-base font-semibold text-foreground mb-2">
              Find Similar Incidents
            </h3>
            <p className="text-sm text-muted-foreground max-w-sm">
              Describe your incident above and our RAG-powered search will find
              the most semantically similar historical cases.
            </p>
            <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
              <span>Powered by</span>
              <span className="text-primary font-medium">Qdrant Vector DB</span>
              <span>+</span>
              <span className="text-purple-400 font-medium">Neo4j Graph</span>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
