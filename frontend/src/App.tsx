import { useEffect, useRef, useState } from "react";
import { io, Socket } from "socket.io-client";
import { useStore } from "@/hooks/useStore";
import { TooltipProvider } from "@/components/ui/tooltip";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import MainPanel from "@/components/MainPanel";
import CryptoPanel from "@/components/CryptoPanel";
import Notification from "@/components/Notification";
import LoginPage from "@/components/LoginPage";
import { Loader2 } from "lucide-react";

export default function App() {
  const { init, theme, appState, activeUser, receiveEmails } = useStore();
  const [notification, setNotification] = useState<{
    message: string;
    type: "success" | "error" | "info";
  } | null>(null);
  // "loading" = init in progress, "login" = needs auth, "ready" = authenticated
  const [status, setStatus] = useState<"loading" | "login" | "ready">("loading");
  const socketRef = useRef<Socket | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    document.documentElement.className = theme;
  }, [theme]);

  useEffect(() => {
    const token = localStorage.getItem("qec-access-token");
    if (!token) {
      // No token at all — skip init, go straight to login
      setStatus("login");
      return;
    }

    init()
      .then(() => {
        const { activeUser } = useStore.getState();
        if (!activeUser) {
          setStatus("login");
        } else {
          setStatus("ready");
        }
      })
      .catch((err: Error) => {
        if (
          err.message.includes("401") ||
          err.message.toLowerCase().includes("authentication") ||
          err.message.toLowerCase().includes("login_required")
        ) {
          setStatus("login");
          return;
        }
        console.error("Init failed:", err);
        setStatus("login");
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (status !== "ready") return;

    const wsEnabled = appState?.features?.websockets ?? false;

    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }

    if (wsEnabled) {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
      // Start with Engine.IO polling, then upgrade when WebSocket is healthy.
      // Some proxies reject a direct WebSocket handshake; polling preserves
      // real-time Socket.IO events instead of leaving the client disconnected.
      const socket = io({ transports: ["polling", "websocket"] });
      socketRef.current = socket;

      socket.on("connect", () => {
        socket.emit("join", { username: activeUser });
      });

      socket.on("new_mail", () => {
        receiveEmails();
      });
    } else {
      pollIntervalRef.current = setInterval(() => {
        receiveEmails();
      }, 30_000);
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, activeUser, appState?.features?.websockets]);

  if (status === "loading") {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-6 h-6 text-primary animate-spin" />
          <span className="text-[11px] text-muted-foreground font-mono">Initializing...</span>
        </div>
      </div>
    );
  }

  if (status === "login") {
    return <LoginPage onSuccess={() => setStatus("ready")} />;
  }

  return (
    <TooltipProvider>
      <div className="h-screen grid grid-rows-[48px_1fr] grid-cols-[220px_1fr_300px] max-xl:grid-cols-[200px_1fr_280px] max-lg:grid-cols-1">
        <Header />
        <Sidebar />
        <MainPanel showNotification={(msg, type) => setNotification({ message: msg, type })} />
        <CryptoPanel />
        {notification && (
          <Notification
            message={notification.message}
            type={notification.type}
            onDismiss={() => setNotification(null)}
          />
        )}
      </div>
    </TooltipProvider>
  );
}
