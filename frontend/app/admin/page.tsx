"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Settings,
  Key,
  Database,
  Cpu,
  Globe,
  Save,
  Eye,
  EyeOff,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { toast } from "sonner";

interface SettingGroup {
  id: string;
  label: string;
  icon: React.ElementType;
  settings: Setting[];
}

interface Setting {
  key: string;
  label: string;
  description: string;
  type: "text" | "number" | "password" | "toggle" | "select";
  value: string | boolean | number;
  options?: string[];
  placeholder?: string;
}

const SETTING_GROUPS: SettingGroup[] = [
  {
    id: "api",
    label: "API Configuration",
    icon: Globe,
    settings: [
      {
        key: "api_url",
        label: "Backend API URL",
        description: "Base URL for the CyberSentinel backend",
        type: "text",
        value: "http://localhost:8000",
        placeholder: "http://localhost:8000",
      },
      {
        key: "ws_url",
        label: "WebSocket URL",
        description: "WebSocket endpoint for real-time updates",
        type: "text",
        value: "ws://localhost:8000",
        placeholder: "ws://localhost:8000",
      },
      {
        key: "api_timeout",
        label: "Request Timeout (ms)",
        description: "Timeout for API requests in milliseconds",
        type: "number",
        value: 60000,
      },
    ],
  },
  {
    id: "llm",
    label: "LLM Settings",
    icon: Cpu,
    settings: [
      {
        key: "llm_model",
        label: "LLM Model",
        description: "Default language model for AI agents",
        type: "select",
        value: "claude-3-5-sonnet-20241022",
        options: [
          "claude-3-5-sonnet-20241022",
          "claude-3-opus-20240229",
          "claude-3-haiku-20240307",
          "gpt-4o",
          "gpt-4-turbo",
        ],
      },
      {
        key: "max_tokens",
        label: "Max Output Tokens",
        description: "Maximum tokens for agent responses",
        type: "number",
        value: 4096,
      },
      {
        key: "temperature",
        label: "Temperature",
        description: "Sampling temperature (0.0 - 1.0)",
        type: "number",
        value: 0.1,
      },
    ],
  },
  {
    id: "database",
    label: "Database",
    icon: Database,
    settings: [
      {
        key: "neo4j_uri",
        label: "Neo4j URI",
        description: "Neo4j graph database connection URI",
        type: "text",
        value: "bolt://localhost:7687",
        placeholder: "bolt://localhost:7687",
      },
      {
        key: "neo4j_user",
        label: "Neo4j Username",
        description: "Neo4j database username",
        type: "text",
        value: "neo4j",
      },
      {
        key: "neo4j_password",
        label: "Neo4j Password",
        description: "Neo4j database password",
        type: "password",
        value: "••••••••",
      },
      {
        key: "qdrant_url",
        label: "Qdrant URL",
        description: "Qdrant vector database URL",
        type: "text",
        value: "http://localhost:6333",
      },
    ],
  },
  {
    id: "keys",
    label: "API Keys",
    icon: Key,
    settings: [
      {
        key: "anthropic_api_key",
        label: "Anthropic API Key",
        description: "API key for Claude language models",
        type: "password",
        value: "sk-ant-••••••••",
        placeholder: "sk-ant-...",
      },
      {
        key: "openai_api_key",
        label: "OpenAI API Key",
        description: "API key for OpenAI models (optional)",
        type: "password",
        value: "",
        placeholder: "sk-...",
      },
    ],
  },
  {
    id: "analysis",
    label: "Analysis Settings",
    icon: Settings,
    settings: [
      {
        key: "max_similar_incidents",
        label: "Max Similar Incidents",
        description: "Number of similar incidents to retrieve",
        type: "number",
        value: 5,
      },
      {
        key: "similarity_threshold",
        label: "Similarity Threshold",
        description: "Minimum similarity score (0.0 - 1.0)",
        type: "number",
        value: 0.7,
      },
      {
        key: "enable_judge_agent",
        label: "Enable Judge Agent",
        description: "Enable quality evaluation by judge agent",
        type: "toggle",
        value: true,
      },
      {
        key: "enable_graph_queries",
        label: "Enable Graph Queries",
        description: "Enable Neo4j knowledge graph queries",
        type: "toggle",
        value: true,
      },
    ],
  },
];

export default function AdminPage() {
  const [settingGroups, setSettingGroups] = useState(SETTING_GROUPS);
  const [activeGroup, setActiveGroup] = useState("api");
  const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(
    new Set(["neo4j_password", "anthropic_api_key", "openai_api_key"])
  );
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<"success" | "error" | null>(null);

  const currentGroup = settingGroups.find((g) => g.id === activeGroup);

  const updateSetting = (
    groupId: string,
    key: string,
    value: string | boolean | number
  ) => {
    setSettingGroups((prev) =>
      prev.map((group) =>
        group.id === groupId
          ? {
              ...group,
              settings: group.settings.map((s) =>
                s.key === key ? { ...s, value } : s
              ),
            }
          : group
      )
    );
  };

  const toggleHidden = (key: string) => {
    setHiddenKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const handleSave = async () => {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 1200));
    setSaving(false);
    toast.success("Settings saved successfully");
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    await new Promise((r) => setTimeout(r, 1500));
    // Simulate random success/failure
    const success = Math.random() > 0.3;
    setTestResult(success ? "success" : "error");
    setTesting(false);
    if (success) {
      toast.success("Connection test successful!");
    } else {
      toast.error("Connection test failed. Check your settings.");
    }
  };

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground">Admin Settings</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Configure CyberSentinel AI platform settings
        </p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar navigation */}
        <div className="w-48 shrink-0">
          <nav className="space-y-1">
            {settingGroups.map((group) => (
              <button
                key={group.id}
                onClick={() => setActiveGroup(group.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-left ${
                  activeGroup === group.id
                    ? "bg-primary/10 text-primary border border-primary/20"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
              >
                <group.icon className="w-4 h-4 shrink-0" />
                {group.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Settings panel */}
        <div className="flex-1">
          {currentGroup && (
            <motion.div
              key={currentGroup.id}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
              className="space-y-6"
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
                  <currentGroup.icon className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-foreground">
                    {currentGroup.label}
                  </h2>
                  <p className="text-xs text-muted-foreground">
                    {currentGroup.settings.length} settings
                  </p>
                </div>
              </div>

              <div className="cyber-card border border-border divide-y divide-border">
                {currentGroup.settings.map((setting) => (
                  <div key={setting.key} className="p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <label className="text-sm font-medium text-foreground block mb-1">
                          {setting.label}
                        </label>
                        <p className="text-xs text-muted-foreground">
                          {setting.description}
                        </p>
                      </div>

                      <div className="w-64 shrink-0">
                        {setting.type === "toggle" ? (
                          <button
                            onClick={() =>
                              updateSetting(
                                currentGroup.id,
                                setting.key,
                                !setting.value
                              )
                            }
                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                              setting.value
                                ? "bg-primary"
                                : "bg-muted border border-border"
                            }`}
                          >
                            <span
                              className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform ${
                                setting.value
                                  ? "translate-x-6"
                                  : "translate-x-1"
                              }`}
                            />
                          </button>
                        ) : setting.type === "select" ? (
                          <select
                            value={setting.value as string}
                            onChange={(e) =>
                              updateSetting(
                                currentGroup.id,
                                setting.key,
                                e.target.value
                              )
                            }
                            className="w-full cyber-input text-sm"
                          >
                            {setting.options?.map((opt) => (
                              <option key={opt} value={opt}>
                                {opt}
                              </option>
                            ))}
                          </select>
                        ) : setting.type === "password" ? (
                          <div className="relative">
                            <input
                              type={hiddenKeys.has(setting.key) ? "password" : "text"}
                              value={setting.value as string}
                              onChange={(e) =>
                                updateSetting(
                                  currentGroup.id,
                                  setting.key,
                                  e.target.value
                                )
                              }
                              placeholder={setting.placeholder}
                              className="w-full cyber-input text-sm pr-9 font-mono"
                            />
                            <button
                              onClick={() => toggleHidden(setting.key)}
                              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                            >
                              {hiddenKeys.has(setting.key) ? (
                                <Eye className="w-4 h-4" />
                              ) : (
                                <EyeOff className="w-4 h-4" />
                              )}
                            </button>
                          </div>
                        ) : (
                          <input
                            type={setting.type === "number" ? "number" : "text"}
                            value={setting.value as string | number}
                            onChange={(e) =>
                              updateSetting(
                                currentGroup.id,
                                setting.key,
                                setting.type === "number"
                                  ? parseFloat(e.target.value)
                                  : e.target.value
                              )
                            }
                            placeholder={setting.placeholder}
                            className="w-full cyber-input text-sm"
                          />
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-3 pt-2">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-2 px-5 py-2.5 bg-primary text-background rounded-lg text-sm font-semibold hover:bg-primary/90 transition-all disabled:opacity-50"
                >
                  <Save className="w-4 h-4" />
                  {saving ? "Saving..." : "Save Settings"}
                </button>

                {(activeGroup === "api" || activeGroup === "database") && (
                  <button
                    onClick={handleTestConnection}
                    disabled={testing}
                    className="flex items-center gap-2 px-4 py-2.5 border border-border rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-50"
                  >
                    <RefreshCw
                      className={`w-4 h-4 ${testing ? "animate-spin" : ""}`}
                    />
                    Test Connection
                  </button>
                )}

                {testResult && (
                  <div
                    className={`flex items-center gap-2 text-sm ${
                      testResult === "success"
                        ? "text-green-400"
                        : "text-red-400"
                    }`}
                  >
                    {testResult === "success" ? (
                      <CheckCircle2 className="w-4 h-4" />
                    ) : (
                      <AlertTriangle className="w-4 h-4" />
                    )}
                    {testResult === "success"
                      ? "Connection successful"
                      : "Connection failed"}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
