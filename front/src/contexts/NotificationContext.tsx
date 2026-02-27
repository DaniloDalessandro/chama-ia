"use client";

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api/client";

// Types
export interface Notification {
  id: string;
  notification_type: string;
  notification_type_display: string;
  title: string;
  message: string;
  chamado: number | null;
  chamado_protocolo: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
  time_ago: string;
}

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  isConnected: boolean;
  isLoading: boolean;
  fetchNotifications: () => Promise<void>;
  markAsRead: (id: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

// Configuration
const WS_RECONNECT_DELAYS = [1000, 2000, 5000, 10000, 30000]; // Exponential backoff
const WS_MAX_RECONNECT_DELAY = 60000; // Max 1 minute
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE_URL = API_BASE_URL.replace("http://", "ws://").replace("https://", "wss://");

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectAttemptsRef = useRef(0);
  const isManuallyClosedRef = useRef(false);

  // Fetch notifications from API
  const fetchNotifications = useCallback(async () => {
    try {
      const response = await apiClient.get("/api/v1/chamados/notifications");
      setNotifications(response.data.results || response.data);

      // Fetch unread count
      const countResponse = await apiClient.get("/api/v1/chamados/notifications/unread-count");
      setUnreadCount(countResponse.data.count);
    } catch (error) {
      console.error("Erro ao buscar notificacoes:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Mark notification as read
  const markAsRead = useCallback(async (id: string) => {
    try {
      await apiClient.post(`/api/v1/chamados/notifications/${id}/mark-read`);

      // Update local state
      setNotifications((prev) =>
        prev.map((notif) =>
          notif.id === id ? { ...notif, is_read: true, read_at: new Date().toISOString() } : notif
        )
      );

      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (error) {
      console.error("Erro ao marcar notificacao como lida:", error);
    }
  }, []);

  // Mark all notifications as read
  const markAllAsRead = useCallback(async () => {
    try {
      const response = await apiClient.post("/api/v1/chamados/notifications/mark-all-read");

      // Update local state
      setNotifications((prev) =>
        prev.map((notif) => ({
          ...notif,
          is_read: true,
          read_at: new Date().toISOString(),
        }))
      );

      setUnreadCount(0);

      toast.success(`${response.data.count} notificacoes marcadas como lidas`);
    } catch (error) {
      console.error("Erro ao marcar todas como lidas:", error);
      toast.error("Erro ao marcar notificacoes");
    }
  }, []);

  // WebSocket connection
  const connectWebSocket = useCallback(() => {
    if (isManuallyClosedRef.current) return;

    // Get JWT token from cookie
    const token = document.cookie
      .split("; ")
      .find((row) => row.startsWith("access_token="))
      ?.split("=")[1];

    if (!token) {
      console.warn("No access token found, skipping WebSocket connection");
      return;
    }

    const wsUrl = `${WS_BASE_URL}/ws/notifications/?token=${token}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connected");
        setIsConnected(true);
        reconnectAttemptsRef.current = 0; // Reset reconnect attempts
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === "connection_established") {
            console.log("WebSocket connection established");
          } else if (data.type === "notification") {
            const notification = data.notification;

            // Add to notifications list
            setNotifications((prev) => [notification, ...prev]);

            // Increment unread count
            if (!notification.is_read) {
              setUnreadCount((prev) => prev + 1);
            }

            // Show toast popup
            toast.info(notification.title, {
              description: notification.message,
              duration: 5000,
            });
          } else if (data.type === "pong") {
            // Ping/pong response
            console.debug("WebSocket pong received");
          }
        } catch (error) {
          console.error("Erro ao processar mensagem WebSocket:", error);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        setIsConnected(false);
      };

      ws.onclose = (event) => {
        console.log("WebSocket closed", event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;

        // Reconnect with exponential backoff
        if (!isManuallyClosedRef.current) {
          const delay = Math.min(
            WS_RECONNECT_DELAYS[reconnectAttemptsRef.current] || WS_MAX_RECONNECT_DELAY,
            WS_MAX_RECONNECT_DELAY
          );

          console.log(`Reconnecting WebSocket in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1})`);

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1;
            connectWebSocket();
          }, delay);
        }
      };
    } catch (error) {
      console.error("Erro ao conectar WebSocket:", error);
    }
  }, []);

  // Send ping to keep connection alive
  useEffect(() => {
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            action: "ping",
            timestamp: new Date().toISOString(),
          })
        );
      }
    }, 30000); // Ping every 30 seconds

    return () => clearInterval(pingInterval);
  }, []);

  // Initialize
  useEffect(() => {
    fetchNotifications();
    connectWebSocket();

    return () => {
      // Cleanup
      isManuallyClosedRef.current = true;

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }

      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [fetchNotifications, connectWebSocket]);

  const value: NotificationContextType = {
    notifications,
    unreadCount,
    isConnected,
    isLoading,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
  };

  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
}

// Hook
export function useNotifications() {
  const context = useContext(NotificationContext);

  if (context === undefined) {
    throw new Error("useNotifications must be used within NotificationProvider");
  }

  return context;
}
