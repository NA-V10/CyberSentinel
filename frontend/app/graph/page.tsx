"use client";

import { useState, useCallback, useEffect } from "react";
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  NodeTypes,
  Handle,
  Position,
  NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Shield,
  Activity,
  GitBranch,
  Layers,
  Network,
  X,
  Maximize2,
  Layout,
  RefreshCw,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { SeverityBadge, ThreatClassBadge } from "@/components/incidents/SeverityBadge";

// Node types with their styling
const nodeStyles = {
  Incident: { bg: "#1e3a5f", border: "#3b82f6", text: "#93c5fd", icon: AlertTriangle },
  AttackType: { bg: "#4a1942", border: "#ef4444", text: "#fca5a5", icon: Activity },
  Asset: { bg: "#1a3a2a", border: "#10b981", text: "#6ee7b7", icon: Shield },
  Mitigation: { bg: "#3a3a1a", border: "#f59e0b", text: "#fcd34d", icon: Layers },
  Protocol: { bg: "#2a1a3a", border: "#7c3aed", text: "#c4b5fd", icon: Network },
};

type NodeTypeKey = keyof typeof nodeStyles;

// Custom node component
function CyberNode({ data, selected }: NodeProps) {
  const style = nodeStyles[data.type as NodeTypeKey] || nodeStyles.Asset;
  const IconComponent = style.icon;

  return (
    <div
      className={`px-3 py-2 rounded-lg border-2 transition-all duration-200 min-w-[120px] ${
        selected ? "shadow-[0_0_20px_rgba(0,212,255,0.5)]" : ""
      }`}
      style={{
        background: style.bg,
        borderColor: selected ? "#00d4ff" : style.border,
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: style.border, width: 8, height: 8 }}
      />
      <div className="flex items-center gap-2">
        <IconComponent className="w-4 h-4 shrink-0" style={{ color: style.text }} />
        <div className="min-w-0">
          <div
            className="text-xs font-semibold truncate max-w-28"
            style={{ color: style.text }}
          >
            {data.label}
          </div>
          <div className="text-xs opacity-70" style={{ color: style.text }}>
            {data.type}
          </div>
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: style.border, width: 8, height: 8 }}
      />
    </div>
  );
}

const nodeTypes: NodeTypes = {
  cyber: CyberNode,
};

// Generate mock graph data
function generateMockGraph() {
  const nodes: Node[] = [
    {
      id: "inc-001",
      type: "cyber",
      position: { x: 300, y: 200 },
      data: {
        label: "Ransomware Attack",
        type: "Incident",
        severity: "critical",
        threat_class: "Ransomware",
        description: "Finance department ransomware infection",
        created_at: "2024-01-15T10:30:00Z",
        source_ip: "192.168.10.45",
      },
    },
    {
      id: "inc-002",
      type: "cyber",
      position: { x: 100, y: 400 },
      data: {
        label: "Phishing Campaign",
        type: "Incident",
        severity: "high",
        threat_class: "Phishing",
        description: "Targeted phishing emails to finance staff",
        created_at: "2024-01-14T09:00:00Z",
      },
    },
    {
      id: "inc-003",
      type: "cyber",
      position: { x: 500, y: 400 },
      data: {
        label: "SSH Brute Force",
        type: "Incident",
        severity: "medium",
        threat_class: "Brute Force",
        description: "SSH brute force on jump server",
        created_at: "2024-01-15T11:00:00Z",
        source_ip: "45.33.32.156",
      },
    },
    {
      id: "att-ransomware",
      type: "cyber",
      position: { x: 300, y: 50 },
      data: { label: "Ransomware", type: "AttackType", family: "Ryuk" },
    },
    {
      id: "att-phishing",
      type: "cyber",
      position: { x: 100, y: 250 },
      data: { label: "Phishing", type: "AttackType", vector: "Email" },
    },
    {
      id: "asset-finance",
      type: "cyber",
      position: { x: 150, y: 550 },
      data: {
        label: "Finance Servers",
        type: "Asset",
        ip_range: "192.168.10.x",
        criticality: "high",
      },
    },
    {
      id: "asset-jumpserver",
      type: "cyber",
      position: { x: 550, y: 550 },
      data: {
        label: "Jump Server",
        type: "Asset",
        ip: "10.0.0.1",
        os: "Ubuntu 22.04",
      },
    },
    {
      id: "mit-isolation",
      type: "cyber",
      position: { x: 50, y: 650 },
      data: {
        label: "Network Isolation",
        type: "Mitigation",
        phase: "immediate",
      },
    },
    {
      id: "mit-backup",
      type: "cyber",
      position: { x: 300, y: 650 },
      data: {
        label: "Restore from Backup",
        type: "Mitigation",
        phase: "short_term",
      },
    },
    {
      id: "mit-mfa",
      type: "cyber",
      position: { x: 550, y: 650 },
      data: { label: "Enable MFA", type: "Mitigation", phase: "long_term" },
    },
    {
      id: "proto-smb",
      type: "cyber",
      position: { x: 450, y: 150 },
      data: { label: "SMB", type: "Protocol", port: 445, version: "3.1" },
    },
    {
      id: "proto-ssh",
      type: "cyber",
      position: { x: 650, y: 300 },
      data: { label: "SSH", type: "Protocol", port: 22, version: "OpenSSH 8.9" },
    },
  ];

  const edges: Edge[] = [
    {
      id: "e1",
      source: "att-ransomware",
      target: "inc-001",
      label: "CLASSIFIED_AS",
      style: { stroke: "#3b82f6", strokeWidth: 1.5 },
      labelStyle: { fill: "#64748b", fontSize: 10 },
    },
    {
      id: "e2",
      source: "att-phishing",
      target: "inc-002",
      label: "CLASSIFIED_AS",
      style: { stroke: "#3b82f6", strokeWidth: 1.5 },
      labelStyle: { fill: "#64748b", fontSize: 10 },
    },
    {
      id: "e3",
      source: "inc-002",
      target: "inc-001",
      label: "LED_TO",
      style: { stroke: "#ef4444", strokeWidth: 2 },
      labelStyle: { fill: "#64748b", fontSize: 10 },
      animated: true,
    },
    {
      id: "e4",
      source: "inc-001",
      target: "asset-finance",
      label: "AFFECTED",
      style: { stroke: "#f59e0b", strokeWidth: 1.5 },
      labelStyle: { fill: "#64748b", fontSize: 10 },
    },
    {
      id: "e5",
      source: "inc-003",
      target: "asset-jumpserver",
      label: "TARGETED",
      style: { stroke: "#f59e0b", strokeWidth: 1.5 },
      labelStyle: { fill: "#64748b", fontSize: 10 },
    },
    {
      id: "e6",
      source: "asset-finance",
      target: "mit-isolation",
      label: "MITIGATED_BY",
      style: { stroke: "#10b981", strokeWidth: 1.5 },
      labelStyle: { fill: "#64748b", fontSize: 10 },
    },
    {
      id: "e7",
      source: "asset-finance",
      target: "mit-backup",
      label: "MITIGATED_BY",
      style: { stroke: "#10b981", strokeWidth: 1.5 },
      labelStyle: { fill: "#64748b", fontSize: 10 },
    },
    {
      id: "e8",
      source: "asset-jumpserver",
      target: "mit-mfa",
      label: "MITIGATED_BY",
      style: { stroke: "#10b981", strokeWidth: 1.5 },
      labelStyle: { fill: "#64748b", fontSize: 10 },
    },
    {
      id: "e9",
      source: "inc-001",
      target: "proto-smb",
      label: "USED_PROTOCOL",
      style: { stroke: "#7c3aed", strokeWidth: 1.5 },
      labelStyle: { fill: "#64748b", fontSize: 10 },
    },
    {
      id: "e10",
      source: "inc-003",
      target: "proto-ssh",
      label: "USED_PROTOCOL",
      style: { stroke: "#7c3aed", strokeWidth: 1.5 },
      labelStyle: { fill: "#64748b", fontSize: 10 },
    },
  ];

  return { nodes, edges };
}

const legendItems = [
  { type: "Incident", color: "#3b82f6", label: "Incident" },
  { type: "AttackType", color: "#ef4444", label: "Attack Type" },
  { type: "Asset", color: "#10b981", label: "Asset" },
  { type: "Mitigation", color: "#f59e0b", label: "Mitigation" },
  { type: "Protocol", color: "#7c3aed", label: "Protocol" },
];

export default function GraphPage() {
  const { nodes: initialNodes, edges: initialEdges } = generateMockGraph();
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handleRefresh = async () => {
    setIsLoading(true);
    await new Promise((r) => setTimeout(r, 1000));
    setIsLoading(false);
  };

  const selectedStyle = selectedNode
    ? nodeStyles[(selectedNode.data.type as NodeTypeKey)] || nodeStyles.Asset
    : null;

  return (
    <DashboardLayout>
      <div className="flex flex-col h-[calc(100vh-8rem)]">
        {/* Header */}
        <div className="flex items-center justify-between mb-4 shrink-0">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Incident Knowledge Graph
            </h1>
            <p className="text-muted-foreground text-sm mt-1">
              Interactive Neo4j-powered incident relationship visualization
            </p>
          </div>
          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border hover:bg-muted text-muted-foreground hover:text-foreground text-sm transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        <div className="flex gap-4 flex-1 overflow-hidden">
          {/* Graph Canvas */}
          <div className="flex-1 cyber-card border border-border overflow-hidden rounded-lg">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              onPaneClick={onPaneClick}
              nodeTypes={nodeTypes}
              fitView
              style={{ background: "#0a0e1a" }}
              defaultEdgeOptions={{
                type: "smoothstep",
              }}
            >
              <Background
                variant={BackgroundVariant.Dots}
                gap={20}
                size={1}
                color="#1f2937"
              />
              <Controls
                style={{
                  background: "#111827",
                  border: "1px solid #1f2937",
                  borderRadius: "8px",
                }}
              />
              <MiniMap
                style={{
                  background: "#111827",
                  border: "1px solid #1f2937",
                  borderRadius: "8px",
                }}
                nodeColor={(node) => {
                  const style = nodeStyles[(node.data?.type as NodeTypeKey)];
                  return style?.border || "#64748b";
                }}
              />
            </ReactFlow>

            {/* Legend */}
            <div className="absolute bottom-16 left-4 bg-card/90 backdrop-blur border border-border rounded-lg p-3">
              <p className="text-xs text-muted-foreground mb-2 font-medium">
                Node Types
              </p>
              <div className="space-y-1.5">
                {legendItems.map((item) => (
                  <div key={item.type} className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-sm border shrink-0"
                      style={{ background: item.color + "30", borderColor: item.color }}
                    />
                    <span className="text-xs text-muted-foreground">
                      {item.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Side Panel - Node Details */}
          <div className="w-72 shrink-0">
            {selectedNode ? (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="cyber-card border border-border h-full overflow-y-auto"
              >
                <div
                  className="flex items-center justify-between p-4 border-b border-border"
                  style={{ borderColor: selectedStyle?.border + "40" }}
                >
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">
                      Node Details
                    </h3>
                    <p
                      className="text-xs font-medium mt-0.5"
                      style={{ color: selectedStyle?.text }}
                    >
                      {selectedNode.data.type}
                    </p>
                  </div>
                  <button
                    onClick={() => setSelectedNode(null)}
                    className="p-1 hover:bg-muted rounded text-muted-foreground"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="p-4 space-y-4">
                  {/* Label */}
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Name</p>
                    <p className="text-sm font-medium text-foreground">
                      {selectedNode.data.label}
                    </p>
                  </div>

                  {/* All properties */}
                  {Object.entries(selectedNode.data)
                    .filter(([key]) => !["label", "type"].includes(key))
                    .map(([key, value]) => (
                      <div key={key}>
                        <p className="text-xs text-muted-foreground mb-1 capitalize">
                          {key.replace(/_/g, " ")}
                        </p>
                        {key === "severity" ? (
                          <SeverityBadge
                            severity={value as "critical" | "high" | "medium" | "low"}
                            size="sm"
                          />
                        ) : key === "threat_class" ? (
                          <ThreatClassBadge threatClass={value as string} />
                        ) : (
                          <p className="text-sm text-foreground font-mono break-all">
                            {String(value)}
                          </p>
                        )}
                      </div>
                    ))}

                  {/* Connected edges */}
                  <div>
                    <p className="text-xs text-muted-foreground mb-2">
                      Connections
                    </p>
                    <div className="space-y-1">
                      {edges
                        .filter(
                          (e) =>
                            e.source === selectedNode.id ||
                            e.target === selectedNode.id
                        )
                        .map((edge) => {
                          const isSource = edge.source === selectedNode.id;
                          const otherNodeId = isSource
                            ? edge.target
                            : edge.source;
                          const otherNode = nodes.find(
                            (n) => n.id === otherNodeId
                          );
                          return (
                            <div
                              key={edge.id}
                              className="flex items-center gap-2 text-xs p-2 rounded bg-muted"
                            >
                              <GitBranch className="w-3 h-3 text-muted-foreground shrink-0" />
                              <div className="min-w-0">
                                <span className="text-muted-foreground">
                                  {isSource ? "→" : "←"}{" "}
                                </span>
                                <span className="text-foreground truncate">
                                  {otherNode?.data.label || otherNodeId}
                                </span>
                                <div
                                  className="text-xs font-medium"
                                  style={{
                                    color: (edge.style?.stroke as string) || "#64748b",
                                  }}
                                >
                                  {edge.label as string}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                </div>
              </motion.div>
            ) : (
              <div className="cyber-card border border-border h-full flex flex-col items-center justify-center text-center p-6">
                <GitBranch className="w-10 h-10 text-muted-foreground/30 mb-3" />
                <p className="text-sm text-muted-foreground">
                  Click a node to view details
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {nodes.length} nodes · {edges.length} relationships
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
