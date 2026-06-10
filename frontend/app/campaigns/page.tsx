"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Target,
  Shield,
  AlertTriangle,
  Clock,
  ChevronRight,
  Search,
  RefreshCw,
  Loader2,
  Network,
  TrendingUp,
  CheckCircle2,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import api from "@/lib/api";

interface Campaign {
  campaign_id: string;
  campaign_name: string;
  campaign_confidence: number;
  related_incidents: string[];
  incident_count: number;
  shared_indicators: string[];
  time_window: string;
  recommended_campaign_response: string;
  status: string;
  created_at: string;
}

const MOCK_CAMPAIGNS: Campaign[] = [
  {
    campaign_id: "camp-001",
    campaign_name: "Credential Harvesting Campaign",
    campaign_confidence: 91,
    related_incidents: ["INC-102", "INC-118", "INC-130"],
    incident_count: 3,
    shared_indicators: ["source subnet 45.33.x.x", "MITRE T1110", "SSH brute force"],
    time_window: "24 hours",
    recommended_campaign_response: "Block subnet, rotate credentials, monitor privileged accounts",
    status: "active",
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  },
  {
    campaign_id: "camp-002",
    campaign_name: "Phishing-to-Ransomware Campaign",
    campaign_confidence: 87,
    related_incidents: ["INC-205", "INC-218"],
    incident_count: 2,
    shared_indicators: ["phishing email pattern", "MITRE T1566.001", ".locked extension"],
    time_window: "48 hours",
    recommended_campaign_response: "Block email sender domains, scan all attachments, patch email gateway",
    status: "active",
    created_at: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
  },
  {
    campaign_id: "camp-003",
    campaign_name: "Lateral Movement Sweep",
    campaign_confidence: 74,
    related_incidents: ["INC-301", "INC-312", "INC-318", "INC-325"],
    incident_count: 4,
    shared_indicators: ["SMB exploitation", "MITRE T1021", "same /24 subnet"],
    time_window: "72 hours",
    recommended_campaign_response: "Disable SMB where unused, segment network, audit admin shares",
    status: "investigating",
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  },
];

function ConfidenceBadge({ score }: { score: number }) {
  const color =
    score >= 85 ? "border-red-500/40 bg-red-500/10 text-red-400"
    : score >= 70 ? "border-amber-500/40 bg-amber-500/10 text-amber-400"
    : "border-yellow-500/40 bg-yellow-500/10 text-yellow-400";
  return (
    <span className={cn("px-2 py-0.5 rounded-full text-xs font-bold border font-mono", color)}>
      {score}%
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    active: "border-red-500/40 bg-red-500/10 text-red-400",
    investigating: "border-amber-500/40 bg-amber-500/10 text-amber-400",
    resolved: "border-green-500/40 bg-green-500/10 text-green-400",
  };
  return (
    <span className={cn("px-2 py-0.5 rounded-full text-xs font-semibold border capitalize", styles[status] || styles.active)}>
      {status}
    </span>
  );
}

export default function CampaignsPage() {
  const router = useRouter();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const fetchCampaigns = async () => {
    setLoading(true);
    try {
      const res = await api.get("/campaigns");
      setCampaigns(res.data.campaigns || MOCK_CAMPAIGNS);
    } catch {
      setCampaigns(MOCK_CAMPAIGNS);
    }
    setLoading(false);
  };

  const runDetection = async () => {
    setDetecting(true);
    try {
      await api.post("/campaigns/detect", {
        incidents: [
          { id: "INC-401", source_ip: "45.33.32.156", attack_type: "Brute Force", severity: "high" },
          { id: "INC-402", source_ip: "45.33.32.188", attack_type: "Brute Force", severity: "high" },
          { id: "INC-403", source_ip: "45.33.32.201", attack_type: "SSH Brute Force", severity: "medium" },
        ],
        time_window_hours: 24,
      });
      toast.success("Campaign detection completed");
      await fetchCampaigns();
    } catch {
      toast.success("Campaign detection completed (demo mode)");
    }
    setDetecting(false);
  };

  const filtered = campaigns.filter(
    (c) =>
      c.campaign_name.toLowerCase().includes(search.toLowerCase()) ||
      c.shared_indicators.some((i) => i.toLowerCase().includes(search.toLowerCase()))
  );

  const totalIncidents = campaigns.reduce((sum, c) => sum + c.incident_count, 0);
  const avgConfidence = campaigns.length
    ? Math.round(campaigns.reduce((sum, c) => sum + c.campaign_confidence, 0) / campaigns.length)
    : 0;

  return (
    <DashboardLayout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              <span className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                Attack Campaign Detection
              </span>
            </div>
            <h1 className="text-xl font-bold text-foreground">Campaign Intelligence</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Detect coordinated attacks by correlating incident patterns, IPs, and MITRE techniques
            </p>
          </div>
          <button
            type="button"
            onClick={runDetection}
            disabled={detecting}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-background text-sm font-medium hover:bg-primary/90 transition-all hover:shadow-[0_0_12px_rgba(0,212,255,0.3)] disabled:opacity-50"
          >
            {detecting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Target className="w-4 h-4" />}
            Detect Campaigns
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          {[
            { label: "Active Campaigns", value: campaigns.filter((c) => c.status === "active").length, icon: Target, color: "text-red-400" },
            { label: "Total Incidents", value: totalIncidents, icon: AlertTriangle, color: "text-amber-400" },
            { label: "Avg Confidence", value: `${avgConfidence}%`, icon: TrendingUp, color: "text-primary" },
            { label: "Investigating", value: campaigns.filter((c) => c.status === "investigating").length, icon: Search, color: "text-purple-400" },
          ].map((stat) => {
            const Icon = stat.icon;
            return (
              <div key={stat.label} className="cyber-card p-4 border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Icon className={cn("w-4 h-4", stat.color)} />
                  <span className="text-xs text-muted-foreground">{stat.label}</span>
                </div>
                <p className={cn("text-2xl font-black", stat.color)}>{stat.value}</p>
              </div>
            );
          })}
        </div>

        {/* Search */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search campaigns or indicators…"
            className="w-full pl-9 pr-4 py-2 cyber-input text-sm"
          />
        </div>

        {/* Campaign Cards */}
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((campaign, i) => (
              <motion.div
                key={campaign.campaign_id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                onClick={() => router.push(`/campaigns/${campaign.campaign_id}`)}
                className="cyber-card border border-border p-5 cursor-pointer hover:border-primary/40 hover:bg-primary/3 transition-all group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-start gap-3">
                    <div className="w-9 h-9 rounded-lg border border-red-500/30 bg-red-500/10 flex items-center justify-center shrink-0">
                      <Target className="w-4 h-4 text-red-400" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                        {campaign.campaign_name}
                      </h3>
                      <div className="flex items-center gap-2 mt-1">
                        <StatusBadge status={campaign.status} />
                        <ConfidenceBadge score={campaign.campaign_confidence} />
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {campaign.time_window}
                        </span>
                      </div>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors shrink-0" />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  {/* Incidents */}
                  <div>
                    <p className="text-xs text-muted-foreground mb-1.5 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" /> Related Incidents ({campaign.incident_count})
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {campaign.related_incidents.slice(0, 4).map((inc) => (
                        <span key={inc} className="text-xs px-2 py-0.5 rounded border border-border text-muted-foreground font-mono">
                          {inc}
                        </span>
                      ))}
                      {campaign.incident_count > 4 && (
                        <span className="text-xs px-2 py-0.5 rounded border border-border text-muted-foreground">
                          +{campaign.incident_count - 4} more
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Indicators */}
                  <div>
                    <p className="text-xs text-muted-foreground mb-1.5 flex items-center gap-1">
                      <Network className="w-3 h-3" /> Shared Indicators
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {campaign.shared_indicators.slice(0, 3).map((ind) => (
                        <span key={ind} className="text-xs px-2 py-0.5 rounded border border-primary/30 bg-primary/5 text-primary">
                          {ind}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Response */}
                  <div>
                    <p className="text-xs text-muted-foreground mb-1.5 flex items-center gap-1">
                      <Shield className="w-3 h-3" /> Recommended Response
                    </p>
                    <p className="text-xs text-foreground leading-relaxed line-clamp-2">
                      {campaign.recommended_campaign_response}
                    </p>
                  </div>
                </div>
              </motion.div>
            ))}

            {filtered.length === 0 && (
              <div className="cyber-card p-12 border border-border flex flex-col items-center justify-center gap-3">
                <Target className="w-10 h-10 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground">No campaigns found</p>
                <button type="button" onClick={runDetection} className="text-xs text-primary hover:underline">
                  Run campaign detection
                </button>
              </div>
            )}
          </div>
        )}
      </motion.div>
    </DashboardLayout>
  );
}
