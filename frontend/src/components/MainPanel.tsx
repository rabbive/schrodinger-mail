import clsx from "clsx";
import { useStore } from "@/hooks/useStore";
import ComposeForm from "./ComposeForm";
import EmailReader from "./EmailReader";
import KeysPanel from "./KeysPanel";
import BenchmarksPanel from "./BenchmarksPanel";
import AuditPanel from "./AuditPanel";
import SettingsPanel from "./SettingsPanel";
import ArchitecturePanel from "./ArchitecturePanel";
import P2PPanel from "./P2PPanel";

type Tab =
  | "compose"
  | "read"
  | "network"
  | "keys"
  | "benchmarks"
  | "audit"
  | "settings"
  | "architecture";

const TABS: { id: Tab; label: string }[] = [
  { id: "compose", label: "Compose" },
  { id: "read", label: "Read" },
  { id: "network", label: "Network" },
  { id: "keys", label: "Keys" },
  { id: "benchmarks", label: "Benchmarks" },
  { id: "audit", label: "Audit Log" },
  { id: "settings", label: "Settings" },
  { id: "architecture", label: "Architecture" },
];

interface Props {
  showNotification: (message: string, type: "success" | "error" | "info") => void;
}

const VALID_TABS = new Set(TABS.map((t) => t.id));

export default function MainPanel({ showNotification }: Props) {
  const { activeTab: rawTab, setActiveTab } = useStore();
  const activeTab: Tab = VALID_TABS.has(rawTab as Tab) ? (rawTab as Tab) : "compose";

  return (
    <main className="overflow-hidden flex flex-col bg-[var(--bg)]">
      {/* Tab bar */}
      <div className="flex items-center gap-0.5 px-3 pt-2 pb-0 overflow-x-auto scrollbar-thin border-b border-[var(--border)]">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              "px-3 py-1.5 text-xs font-medium rounded-t transition-colors whitespace-nowrap",
              activeTab === tab.id
                ? "bg-[var(--surface)] text-accent border border-[var(--border)] border-b-transparent -mb-px"
                : "text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-[var(--surface2)]",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4 scrollbar-thin">
        {activeTab === "compose" && <ComposeForm showNotification={showNotification} />}
        {activeTab === "read" && <EmailReader />}
        {activeTab === "network" && <P2PPanel />}
        {activeTab === "keys" && <KeysPanel />}
        {activeTab === "benchmarks" && <BenchmarksPanel />}
        {activeTab === "audit" && <AuditPanel />}
        {activeTab === "settings" && <SettingsPanel />}
        {activeTab === "architecture" && <ArchitecturePanel />}
      </div>
    </main>
  );
}
