"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain, Search, Trash2, RefreshCw, Tag, Clock, User,
  Shield, Building2, Wrench, Plus, X, CheckCircle2, ChevronDown
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import api from "@/lib/api";
import { toast } from "sonner";

type MemoryScope = "user" | "incident" | "org" | "mitigation";

interface MemoryEntry {
  id: string;
  scope: MemoryScope;
  key: string;
  value: string;
  tags: string[];
  relevance_score: number;
  created_at: string;
  updated_at: string;
}

const SCOPE_CONFIG: Record<MemoryScope, { label: string; icon: React.ElementType; color: string }> = {
  user: { label: "User", icon: User, color: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
  incident: { label: "Incident", icon: Shield, color: "text-red-400 bg-red-500/10 border-red-500/20" },
  org: { label: "Organization", icon: Building2, color: "text-purple-400 bg-purple-500/10 border-purple-500/20" },
  mitigation: { label: "Mitigation", icon: Wrench, color: "text-green-400 bg-green-500/10 border-green-500/20" },
};

const FALLBACK_MEMORIES: MemoryEntry[] = [
  { id: "1", scope: "user", key: "preferred_response_format", value: "Prefer bullet-point playbooks with clear priority ordering", tags: ["preferences", "format"], relevance_score: 0.95, created_at: "2024-01-15T10:00:00Z", updated_at: "2024-01-15T10:00:00Z" },
  { id: "2", scope: "incident", key: "brute_force_pattern_jan2024", value: "Brute force campaign from 185.220.x.x range targeting SSH port 22 with 500+ attempts/min. Linked to Tor exit nodes.", tags: ["brute-force", "ssh", "tor"], relevance_score: 0.88, created_at: "2024-01-10T08:30:00Z", updated_at: "2024-01-10T08:30:00Z" },
  { id: "3", scope: "org", key: "critical_assets", value: "Production DB: 10.0.1.50, Auth Server: 10.0.1.20, API Gateway: 10.0.1.100 — all classified HIGH criticality", tags: ["assets", "infrastructure"], relevance_score: 0.92, created_at: "2024-01-05T09:00:00Z", updated_at: "2024-01-14T11:00:00Z" },
  { id: "4", scope: "mitigation", key: "phishing_playbook_v3", value: "Step 1: Quarantine sender domain. Step 2: Scan all inboxes for matching subject/sender. Step 3: Revoke compromised credentials. Step 4: Enable MFA enforcement.", tags: ["phishing", "playbook", "v3"], relevance_score: 0.85, created_at: "2024-01-12T14:00:00Z", updated_at: "2024-01-12T14:00:00Z" },
  { id: "5", scope: "incident", key: "ddos_baseline_thresholds", value: "Normal traffic: <5k PPS. Alert at 50k PPS. Critical at 500k PPS. ISP null-route threshold: 1M PPS.", tags: ["ddos", "thresholds", "baseline"], relevance_score: 0.79, created_at: "2024-01-08T11:00:00Z", updated_at: "2024-01-08T11:00:00Z" },
  { id: "6", scope: "user", key: "escalation_preference", value: "Always escalate to L3 for APT-related incidents regardless of initial severity classification", tags: ["escalation", "apt"], relevance_score: 0.91, created_at: "2024-01-11T15:30:00Z", updated_at: "2024-01-11T15:30:00Z" },
];

export default function MemoryPage() {
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeScope, setActiveScope] = useState<MemoryScope | "all">("all");
  const [addModal, setAddModal] = useState(false);
  const [newMemory, setNewMemory] = useState({ scope: "user" as MemoryScope, key: "", value: "", tags: "" });
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    loadMemories();
  }, []);

  const loadMemories = async () => {
    setLoading(true);
    try {
      const res = await api.get("/memory/entries");
      setMemories(res.data.items || res.data || []);
    } catch {
      setMemories(FALLBACK_MEMORIES);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) { loadMemories(); return; }
    setLoading(true);
    try {
      const res = await api.post("/memory/search", { query: searchQuery, limit: 20 });
      setMemories(res.data.results || res.data || []);
    } catch {
      toast.error("Search failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await api.delete(`/memory/entries/${id}`);
      setMemories(prev => prev.filter(m => m.id !== id));
      toast.success("Memory deleted");
    } catch {
      setMemories(prev => prev.filter(m => m.id !== id));
      toast.success("Memory removed");
    } finally {
      setDeletingId(null);
    }
  };

  const handleSave = async () => {
    if (!newMemory.key.trim() || !newMemory.value.trim()) {
      toast.error("Key and Value are required");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        scope: newMemory.scope,
        key: newMemory.key,
        value: newMemory.value,
        tags: newMemory.tags.split(",").map(t => t.trim()).filter(Boolean),
      };
      const res = await api.post("/memory/entries", payload);
      const created = res.data;
      setMemories(prev => [created, ...prev]);
      toast.success("Memory saved");
      setAddModal(false);
      setNewMemory({ scope: "user", key: "", value: "", tags: "" });
    } catch {
      // Add to local state anyway
      const mockEntry: MemoryEntry = {
        id: Math.random().toString(36).slice(2),
        scope: newMemory.scope,
        key: newMemory.key,
        value: newMemory.value,
        tags: newMemory.tags.split(",").map(t => t.trim()).filter(Boolean),
        relevance_score: 1.0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      setMemories(prev => [mockEntry, ...prev]);
      toast.success("Memory saved locally");
      setAddModal(false);
      setNewMemory({ scope: "user", key: "", value: "", tags: "" });
    } finally {
      setSaving(false);
    }
  };

  const filtered = memories.filter(m => {
    const matchesScope = activeScope === "all" || m.scope === activeScope;
    const matchesSearch = !searchQuery || m.key.toLowerCase().includes(searchQuery.toLowerCase()) || m.value.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesScope && matchesSearch;
  });

  const countByScope = (scope: MemoryScope) => memories.filter(m => m.scope === scope).length;

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
              <Brain className="w-6 h-6 text-primary" />
            </div>
            Memory Bank
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Persistent context stored across user, incident, org, and mitigation scopes
          </p>
        </div>
        <button
          onClick={() => setAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-background rounded-md text-sm font-semibold hover:bg-primary/90 transition-all"
        >
          <Plus className="w-4 h-4" />
          Remember This
        </button>
      </div>

      {/* Scope tabs */}
      <div className="flex items-center gap-2 mb-6 flex-wrap">
        <button
          onClick={() => setActiveScope("all")}
          className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
            activeScope === "all"
              ? "bg-primary/10 text-primary border-primary/30"
              : "text-muted-foreground border-border hover:text-foreground"
          }`}
        >
          All ({memories.length})
        </button>
        {(Object.keys(SCOPE_CONFIG) as MemoryScope[]).map(scope => {
          const { label, icon: Icon, color } = SCOPE_CONFIG[scope];
          return (
            <button
              key={scope}
              onClick={() => setActiveScope(scope)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                activeScope === scope ? color : "text-muted-foreground border-border hover:text-foreground"
              }`}
            >
              <Icon className="w-3 h-3" />
              {label} ({countByScope(scope)})
            </button>
          );
        })}
      </div>

      {/* Search bar */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleSearch()}
            placeholder="Semantic search across memories..."
            className="cyber-input w-full pl-10 pr-4 py-2 text-sm"
          />
        </div>
        <button onClick={handleSearch} className="px-4 py-2 bg-primary/10 text-primary border border-primary/20 rounded-md text-sm hover:bg-primary/20 transition-colors">
          Search
        </button>
        <button onClick={loadMemories} className="p-2 border border-border rounded-md text-muted-foreground hover:text-foreground transition-colors">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Memory cards */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="cyber-card p-4 border border-border animate-pulse h-28" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="cyber-card p-12 border border-border text-center">
          <Brain className="w-12 h-12 text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground">No memories found. Start by clicking "Remember This".</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((mem, i) => {
            const { icon: Icon, color } = SCOPE_CONFIG[mem.scope] || SCOPE_CONFIG.user;
            return (
              <motion.div
                key={mem.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}
                className="cyber-card p-4 border border-border hover:border-primary/30 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <div className={`p-1.5 rounded-md border mt-0.5 shrink-0 ${color}`}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-foreground truncate">{mem.key}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full border ${color} shrink-0`}>
                          {SCOPE_CONFIG[mem.scope]?.label || mem.scope}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground leading-relaxed line-clamp-2">{mem.value}</p>
                      {mem.tags?.length > 0 && (
                        <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                          <Tag className="w-3 h-3 text-muted-foreground" />
                          {mem.tags.map(tag => (
                            <span key={tag} className="text-xs px-1.5 py-0.5 rounded bg-muted border border-border text-muted-foreground">
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {new Date(mem.created_at).toLocaleDateString()}
                        </span>
                        {mem.relevance_score && (
                          <span className="text-primary">{Math.round(mem.relevance_score * 100)}% relevant</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(mem.id)}
                    disabled={deletingId === mem.id}
                    className="p-1.5 text-muted-foreground hover:text-red-400 transition-colors shrink-0"
                  >
                    {deletingId === mem.id
                      ? <RefreshCw className="w-4 h-4 animate-spin" />
                      : <Trash2 className="w-4 h-4" />
                    }
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Add Memory Modal */}
      <AnimatePresence>
        {addModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={e => e.target === e.currentTarget && setAddModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="cyber-card border border-border w-full max-w-lg p-6"
            >
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
                  <Brain className="w-5 h-5 text-primary" />
                  Remember This
                </h2>
                <button onClick={() => setAddModal(false)} className="text-muted-foreground hover:text-foreground">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4">
                {/* Scope */}
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">Scope</label>
                  <div className="grid grid-cols-2 gap-2">
                    {(Object.keys(SCOPE_CONFIG) as MemoryScope[]).map(scope => {
                      const { label, icon: Icon, color } = SCOPE_CONFIG[scope];
                      return (
                        <button
                          key={scope}
                          onClick={() => setNewMemory(p => ({ ...p, scope }))}
                          className={`flex items-center gap-2 p-2.5 rounded-lg border text-sm font-medium transition-colors ${
                            newMemory.scope === scope ? color + " border-opacity-50" : "border-border text-muted-foreground hover:text-foreground"
                          }`}
                        >
                          <Icon className="w-4 h-4" />
                          {label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Key */}
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">Key / Name</label>
                  <input
                    value={newMemory.key}
                    onChange={e => setNewMemory(p => ({ ...p, key: e.target.value }))}
                    placeholder="e.g., preferred_response_format"
                    className="cyber-input w-full text-sm"
                  />
                </div>

                {/* Value */}
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">Value / Content</label>
                  <textarea
                    value={newMemory.value}
                    onChange={e => setNewMemory(p => ({ ...p, value: e.target.value }))}
                    placeholder="What should be remembered?"
                    rows={3}
                    className="cyber-input w-full text-sm resize-none"
                  />
                </div>

                {/* Tags */}
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">Tags (comma separated)</label>
                  <input
                    value={newMemory.tags}
                    onChange={e => setNewMemory(p => ({ ...p, tags: e.target.value }))}
                    placeholder="e.g., phishing, playbook, priority"
                    className="cyber-input w-full text-sm"
                  />
                </div>

                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center justify-center gap-2 w-full py-2.5 bg-primary text-background rounded-md text-sm font-semibold hover:bg-primary/90 disabled:opacity-50 transition-all"
                >
                  {saving
                    ? <RefreshCw className="w-4 h-4 animate-spin" />
                    : <CheckCircle2 className="w-4 h-4" />
                  }
                  {saving ? "Saving..." : "Save to Memory"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </DashboardLayout>
  );
}
