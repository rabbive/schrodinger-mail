import { useEffect, useState } from "react";
import { useStore } from "@/hooks/useStore";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import MainPanel from "@/components/MainPanel";
import CryptoPanel from "@/components/CryptoPanel";
import Notification from "@/components/Notification";

export default function App() {
  const { init, theme, appState } = useStore();
  const [notification, setNotification] = useState<{
    message: string;
    type: "success" | "error" | "info";
  } | null>(null);
  const [ready, setReady] = useState(false);

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
