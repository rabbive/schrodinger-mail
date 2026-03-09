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
import DemoStoryline from "./DemoStoryline";
import AttackLab from "./AttackLab";
import TofuPanel from "./TofuPanel";

type Tab =
  | "demo-guide"
  | "attack-lab"
  | "compose"
  | "read"
  | "network"
  | "tofu"
  | "keys"
  | "benchmarks"
  | "audit"
  | "settings"
  | "architecture";

const TABS: { id: Tab; label: string }[] = [
  { id: "demo-guide", label: "Demo Guide" },
  { id: "attack-lab", label: "Attack Lab" },
  { id: "compose", label: "Compose" },
  { id: "read", label: "Read" },
  { id: "network", label: "Network" },
  { id: "tofu", label: "Trust (TOFU)" },
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
  const activeTab: Tab = VALID_TABS.has(rawTab as Tab) ? (rawTab as Tab) : "demo-guide";

  return (
    <main className="overflow-hidden flex flex-col bg-[var(--bg)]">
      {/* Tab bar */}
      <div className="flex items-center gap-0 px-2 pt-0 pb-0 overflow-x-auto scrollbar-thin bg-[var(--surface)] border-b border-[var(--border)]">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              "px-3 py-2 text-[12px] font-medium transition-colors whitespace-nowrap border-b-2",
              activeTab === tab.id
                ? "text-[var(--text)] border-b-accent bg-[var(--bg)]"
                : "text-[var(--text-muted)] border-b-transparent hover:text-[var(--text-dim)] hover:bg-[var(--surface2)]",
              (tab.id === "demo-guide" || tab.id === "attack-lab") &&
                activeTab !== tab.id &&
                "text-accent/60",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-5 scrollbar-thin">
        {activeTab === "demo-guide" && <DemoStoryline />}
        {activeTab === "attack-lab" && <AttackLab />}
        {activeTab === "compose" && <ComposeForm showNotification={showNotification} />}
        {activeTab === "read" && <EmailReader />}
        {activeTab === "network" && <P2PPanel />}
        {activeTab === "tofu" && <TofuPanel />}
        {activeTab === "keys" && <KeysPanel />}
        {activeTab === "benchmarks" && <BenchmarksPanel />}
        {activeTab === "audit" && <AuditPanel />}
        {activeTab === "settings" && <SettingsPanel />}
        {activeTab === "architecture" && <ArchitecturePanel />}
      </div>
    </main>
  );
}
