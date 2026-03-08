import { useEffect, useRef, useState } from "react";
import { io, Socket } from "socket.io-client";
import { useStore } from "@/hooks/useStore";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import MainPanel from "@/components/MainPanel";
import CryptoPanel from "@/components/CryptoPanel";
import Notification from "@/components/Notification";

export default function App() {
  const { init, theme, appState, activeUser, receiveEmails } = useStore();
  const [notification, setNotification] = useState<{
    message: string;
    type: "success" | "error" | "info";
  } | null>(null);
  const [ready, setReady] = useState(false);
  const socketRef = useRef<Socket | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    document.documentElement.className = theme;
  }, [theme]);

  useEffect(() => {
    init()
      .then(() => setReady(true))
      .catch((err) => {
        console.error("Init failed:", err);
        setReady(true);
      });
  }, [init]);

  // Auto-receive: Socket.IO with polling fallback
  useEffect(() => {
    if (!ready) return;

    const wsEnabled = appState?.features?.websockets ?? false;

    // Clear previous interval if any
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }

    if (wsEnabled) {
      // Disconnect previous socket before creating a new one
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
      const socket = io({ transports: ["websocket", "polling"] });
      socketRef.current = socket;

      socket.on("connect", () => {
        socket.emit("join", { username: activeUser });
      });

      socket.on("new_mail", () => {
        receiveEmails();
      });
    } else {
      // Polling fallback: check every 30 seconds
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
  }, [ready, activeUser, appState?.features?.websockets]);

  if (!ready || !appState) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin w-8 h-8 border-4 border-accent border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="h-screen grid grid-rows-[52px_1fr] grid-cols-[240px_1fr_320px] max-xl:grid-cols-[200px_1fr_300px] max-lg:grid-cols-1">
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
  );
}
