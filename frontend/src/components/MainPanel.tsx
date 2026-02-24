import { useState } from "react";
import clsx from "clsx";
import ComposeForm from "./ComposeForm";
import EmailReader from "./EmailReader";
import KeysPanel from "./KeysPanel";
import BenchmarksPanel from "./BenchmarksPanel";
import AuditPanel from "./AuditPanel";
import SettingsPanel from "./SettingsPanel";
import ArchitecturePanel from "./ArchitecturePanel";

type Tab =
  | "compose"
  | "read"
  | "contacts"
  | "keys"
  | "benchmarks"
  | "audit"
  | "settings"
  | "architecture";

const TABS: { id: Tab; label: string }[] = [
  { id: "compose", label: "Compose" },
  { id: "read", label: "Read" },
  { id: "contacts", label: "Contacts" },
  { id: "keys", label: "Keys" },
  { id: "benchmarks", label: "Benchmarks" },
  { id: "audit", label: "Audit Log" },
  { id: "settings", label: "Settings" },
  { id: "architecture", label: "Architecture" },
];

interface Props {
  showNotification: (message: string, type: "success" | "error" | "info") => void;
}

export default function MainPanel({ showNotification }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("compose");

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
        {activeTab === "keys" && <KeysPanel />}
        {activeTab === "benchmarks" && <BenchmarksPanel />}
        {activeTab === "audit" && <AuditPanel />}
        {activeTab === "settings" && <SettingsPanel />}
        {activeTab === "architecture" && <ArchitecturePanel />}
        {activeTab === "contacts" && (
          <div className="text-sm text-[var(--text-dim)]">
            Contact management — use the API at <code>/api/contacts/username</code>.
          </div>
        )}
      </div>
    </main>
  );
}
