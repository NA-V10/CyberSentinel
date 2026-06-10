"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Target, Shield, AlertTriangle, Clock, ArrowLeft,
  Network, Map, CheckCircle2, Activity, Loader2, ChevronRight,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { cn } from "@/lib/utils";
import api from "@/lib/api";

interface CampaignDetail {
  campaign_id: string;
  campaign_name: string;
  campaign_confidence: number;
  related_incidents: string[];
  incident_count: number;
  shared_indicators: string[];
  time_window: string;
  recommended_campaign_response: string;
  attack_narrative: string;
  threat_actor_profile: string;
  mitre_techniques: { techniques: string[] };
  source_subnets: { ips: string[] };
  targeted_assets: { assets: string[] };
  timeline: { time: string; event: string }[];
  status: string;
  created_at: string;
}

const MOCK_DETAIL: CampaignDetail = {
  campaign_id: "camp-001",
  campaign_name: "Credential Harvesting Campaign",
  campaign_confidence: 91,
  related_incidents: ["INC-102", "INC-118", "INC-130"],
  incident_count: 3,
  shared_indicators: ["source subnet 45.33.x.x", "MITRE T1110", "SSH brute force"],
  time_window: "24 hours",
  recommended_campaign_response: "Block subnet, rotate credentials, monitor privileged accounts",
  attack_narrative: "A coordinated credential harvesting campaign targeting SSH services across the infrastructure. Consistent source subnet and technique pattern indicates automated tooling. The threat actor appears to be systematically probing for weak credentials across exposed management ports.",
  threat_actor_profile: "Intermediate sophistication — automated credential stuffing with manual follow-up on successful authentications",
  mitre_techniques: { techniques: ["T1110", "T1078", "T1110.001"] },
  source_subnets: { ips: ["45.33.32.156", "45.33.32.188", "45.33.32.201"] },
  targeted_assets: { assets: ["192.168.1.10", "192.168.1.22", "192.168.1.35"] },
  timeline: [
    { time: "T+0h", event: "First SSH brute force detected on 192.168.1.10 (INC-102)" },
    { time: "T+4h", event: "Same subnet targets 192.168.1.22 — 847 failed attempts (INC-118)" },
    { time: "T+18h", event: "Credential success on 192.168.1.35, active session established (INC-130)" },
  ],
  status: "active",
  created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
};

export default function CampaignDetailPage() {
  const params = useParams();
  const router = useRouter();
  const campaignId = params?.campaignId as string;
  const [campaign, setCampaign] = useState<CampaignDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await api.get(`/campaigns/${campaignId}`);
        setCampaign(res.data);
      } catch {
        setCampaign(MOCK_DETAIL);
      }
      setLoading(false);
    };
    if (campaignId) fetch();
  }, [campaignId]);

  if (loading || !campaign) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        {/* Back + Header */}
        <div className="flex items-start gap-4 mb-6">
          <button type="button" onClick={() => router.push("/campaigns")} className="mt-1 p-1.5 rounded-lg border border-border hover:bg-muted text-muted-foreground transition-colors">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              <span className="text-xs font-mono text-muted-foreground uppercase tracking-widest">Campaign Detail</span>
            </div>
            <h1 className="text-xl font-bold text-foreground">{campaign.campaign_name}</h1>
            <div className="flex items-center gap-3 mt-1.5">
              <span className="px-2 py-0.5 rounded-full text-xs font-bold border border-red-500/40 bg-red-500/10 text-red-400 font-mono">{campaign.campaign_confidence}% confidence</span>
              <span className="px-2 py-0.5 rounded-full text-xs font-semibold border border-amber-500/40 bg-amber-500/10 text-amber-400 capitalize">{campaign.status}</span>
              <span className="text-xs text-muted-foreground flex items-center gap-1"><Clock className="w-3 h-3" />{campaign.time_window}</span>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6">
          {[
            { id: "overview", label: "Overview", icon: Activity },
            { id: "timeline", label: "Timeline", icon: Clock },
            { id: "indicators", label: "Indicators", icon: Network },
            { id: "response", label: "Response", icon: Shield },
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all",
                  activeTab === tab.id ? "bg-primary text-background" : "text-muted-foreground hover:text-foreground hover:bg-muted"
                )}
              >
                <Icon className="w-3.5 h-3.5" /> {tab.label}
              </button>
            );
          })}
        </div>

        {/* Overview */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2 space-y-4">
              <div className="cyber-card p-5 border border-border">
                <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2"><Target className="w-4 h-4 text-red-400" /> Attack Narrative</h3>
                <p className="text-sm text-foreground leading-relaxed">{campaign.attack_narrative}</p>
              </div>
              <div className="cyber-card p-5 border border-border">
                <h3 className="text-sm font-semibold text-foreground mb-3">Threat Actor Profile</h3>
                <p className="text-sm text-muted-foreground">{campaign.threat_actor_profile}</p>
              </div>
              <div className="cyber-card p-5 border border-border">
                <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-primary" /> Related Incidents</h3>
                <div className="flex flex-wrap gap-2">
                  {campaign.related_incidents.map((inc) => (
                    <span key={inc} className="px-3 py-1 rounded-lg border border-primary/30 bg-primary/5 text-primary text-xs font-mono cursor-pointer hover:bg-primary/15 transition-colors">
                      {inc}
                    </span>
                  ))}
                </div>
              </div>
            </div>
            <div className="space-y-4">
              <div className="cyber-card p-5 border border-border">
                <h3 className="text-xs text-muted-foreground mb-3">MITRE Techniques</h3>
                <div className="space-y-2">
                  {(campaign.mitre_techniques?.techniques || []).map((t) => (
                    <span key={t} className="flex items-center gap-2 text-xs">
                      <Map className="w-3 h-3 text-purple-400" />
                      <span className="font-mono text-purple-400">{t}</span>
                    </span>
                  ))}
                </div>
              </div>
              <div className="cyber-card p-5 border border-border">
                <h3 className="text-xs text-muted-foreground mb-3">Source IPs</h3>
                <div className="space-y-1">
                  {(campaign.source_subnets?.ips || []).map((ip) => (
                    <span key={ip} className="block text-xs font-mono text-red-400">{ip}</span>
                  ))}
                </div>
              </div>
              <div className="cyber-card p-5 border border-border">
                <h3 className="text-xs text-muted-foreground mb-3">Targeted Assets</h3>
                <div className="space-y-1">
                  {(campaign.targeted_assets?.assets || []).map((a) => (
                    <span key={a} className="block text-xs font-mono text-foreground">{a}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Timeline */}
        {activeTab === "timeline" && (
          <div className="cyber-card p-5 border border-border">
            <h3 className="text-sm font-semibold text-foreground mb-4">Campaign Timeline</h3>
            <div className="relative space-y-0">
              {(campaign.timeline || []).map((event, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="flex gap-4 pb-6 last:pb-0"
                >
                  <div className="flex flex-col items-center">
                    <div className="w-3 h-3 rounded-full bg-primary border-2 border-background shrink-0 mt-1" />
                    {i < (campaign.timeline || []).length - 1 && <div className="w-px flex-1 bg-border mt-1" />}
                  </div>
                  <div className="flex-1 pb-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono font-bold text-primary">{event.time}</span>
                    </div>
                    <p className="text-sm text-foreground">{event.event}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Indicators */}
        {activeTab === "indicators" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="cyber-card p-5 border border-border">
              <h3 className="text-sm font-semibold text-foreground mb-3">Shared Indicators</h3>
              <div className="space-y-2">
                {campaign.shared_indicators.map((ind, i) => (
                  <div key={i} className="flex items-center gap-2 p-2 rounded bg-muted/50 border border-border">
                    <CheckCircle2 className="w-3.5 h-3.5 text-primary shrink-0" />
                    <span className="text-sm text-foreground">{ind}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="cyber-card p-5 border border-border">
              <h3 className="text-sm font-semibold text-foreground mb-3">Cluster Analysis</h3>
              <div className="space-y-3 text-xs">
                <div className="flex items-center justify-between py-2 border-b border-border">
                  <span className="text-muted-foreground">Incidents grouped</span>
                  <span className="font-mono font-bold text-foreground">{campaign.incident_count}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-border">
                  <span className="text-muted-foreground">Time window</span>
                  <span className="font-mono text-foreground">{campaign.time_window}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-border">
                  <span className="text-muted-foreground">Campaign confidence</span>
                  <span className="font-mono font-bold text-red-400">{campaign.campaign_confidence}%</span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-muted-foreground">MITRE techniques matched</span>
                  <span className="font-mono text-foreground">{(campaign.mitre_techniques?.techniques || []).length}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Response */}
        {activeTab === "response" && (
          <div className="cyber-card p-6 border border-green-500/20 bg-green-500/5">
            <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
              <Shield className="w-4 h-4 text-green-400" /> Recommended Campaign Response
            </h3>
            <p className="text-sm text-foreground leading-relaxed mb-4">{campaign.recommended_campaign_response}</p>
            <div className="space-y-2">
              {["Block all IPs from identified source subnets at perimeter firewall", "Rotate credentials for all potentially affected accounts immediately", "Enable enhanced monitoring on privileged accounts for 72 hours", "Deploy honeypot SSH services to track further activity", "Brief CISO on campaign scope and potential attribution"].map((step, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <span className="font-mono font-bold text-green-400 shrink-0">{String(i + 1).padStart(2, "0")}.</span>
                  <span className="text-foreground">{step}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </motion.div>
    </DashboardLayout>
  );
}
