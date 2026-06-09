"use client";

import { useState, useEffect, useRef, useCallback } from "react";

export type WebSocketStatus =
  | "connecting"
  | "connected"
  | "disconnected"
  | "error"
  | "reconnecting";

export interface AgentMessage {
  type: "agent_update" | "result" | "error" | "ping" | "connected" | "status";
  agent?: string;
  status?: "pending" | "running" | "complete" | "error";
  message?: string;
  data?: Record<string, unknown>;
  timestamp?: string;
  session_id?: string;
  result?: Record<string, unknown>;
  error?: string;
}

interface UseWebSocketOptions {
  sessionId: string;
  onMessage?: (message: AgentMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  reconnectDelay?: number;
  maxReconnects?: number;
  enabled?: boolean;
}

interface UseWebSocketReturn {
  status: WebSocketStatus;
  messages: AgentMessage[];
  lastMessage: AgentMessage | null;
  sendMessage: (data: Record<string, unknown>) => void;
  disconnect: () => void;
  reconnect: () => void;
  clearMessages: () => void;
}

export function useWebSocket({
  sessionId,
  onMessage,
  onConnect,
  onDisconnect,
  onError,
  reconnectDelay = 2000,
  maxReconnects = 5,
  enabled = true,
}: UseWebSocketOptions): UseWebSocketReturn {
  const [status, setStatus] = useState<WebSocketStatus>("disconnected");
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [lastMessage, setLastMessage] = useState<AgentMessage | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(true);

  const connect = useCallback(() => {
    if (!enabled || !sessionId) return;

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsBase = (typeof window !== "undefined"
      ? process.env.NEXT_PUBLIC_WS_URL
      : undefined) || "ws://localhost:8000";
    const url = `${wsBase}/api/v1/ws/analyze/${sessionId}`;
    setStatus("connecting");

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
        reconnectCountRef.current = 0;
        onConnect?.();
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          const parsed: AgentMessage = JSON.parse(event.data as string);
          setMessages((prev) => [...prev, parsed]);
          setLastMessage(parsed);
          onMessage?.(parsed);
        } catch {
          console.error("Failed to parse WebSocket message:", event.data);
        }
      };

      ws.onerror = (event: Event) => {
        setStatus("error");
        onError?.(event);
      };

      ws.onclose = () => {
        setStatus("disconnected");
        onDisconnect?.();

        // Attempt reconnection if allowed
        if (
          shouldReconnectRef.current &&
          reconnectCountRef.current < maxReconnects
        ) {
          reconnectCountRef.current += 1;
          setStatus("reconnecting");
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay * reconnectCountRef.current);
        }
      };
    } catch (err) {
      console.error("WebSocket connection failed:", err);
      setStatus("error");
    }
  }, [
    sessionId,
    enabled,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    reconnectDelay,
    maxReconnects,
  ]);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setStatus("disconnected");
  }, []);

  const reconnect = useCallback(() => {
    shouldReconnectRef.current = true;
    reconnectCountRef.current = 0;
    connect();
  }, [connect]);

  const sendMessage = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn("WebSocket is not connected. Cannot send message.");
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setLastMessage(null);
  }, []);

  // Connect on mount / when sessionId changes
  useEffect(() => {
    if (enabled && sessionId) {
      shouldReconnectRef.current = true;
      connect();
    }

    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [sessionId, enabled]);

  return {
    status,
    messages,
    lastMessage,
    sendMessage,
    disconnect,
    reconnect,
    clearMessages,
  };
}
