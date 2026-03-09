import { cn } from "@/lib/utils";
import { useStore } from "@/hooks/useStore";
import { ScrollArea } from "@/components/ui/scroll-area";
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
import {
  BookOpen,
  FlaskConical,
  PenSquare,
  BookOpenCheck,
  Globe,
  ShieldCheck,
  KeyRound,
  Gauge,
  ClipboardList,
  Settings,
  Layers,
} from "lucide-react";

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

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "demo-guide", label: "Demo Guide", icon: <BookOpen className="w-3.5 h-3.5" /> },
  { id: "attack-lab", label: "Attack Lab", icon: <FlaskConical className="w-3.5 h-3.5" /> },
  { id: "compose", label: "Compose", icon: <PenSquare className="w-3.5 h-3.5" /> },
  { id: "read", label: "Read", icon: <BookOpenCheck className="w-3.5 h-3.5" /> },
  { id: "network", label: "Network", icon: <Globe className="w-3.5 h-3.5" /> },
  { id: "tofu", label: "Trust (TOFU)", icon: <ShieldCheck className="w-3.5 h-3.5" /> },
  { id: "keys", label: "Keys", icon: <KeyRound className="w-3.5 h-3.5" /> },
  { id: "benchmarks", label: "Benchmarks", icon: <Gauge className="w-3.5 h-3.5" /> },
  { id: "audit", label: "Audit Log", icon: <ClipboardList className="w-3.5 h-3.5" /> },
  { id: "settings", label: "Settings", icon: <Settings className="w-3.5 h-3.5" /> },
  { id: "architecture", label: "Architecture", icon: <Layers className="w-3.5 h-3.5" /> },
];

interface Props {
  showNotification: (message: string, type: "success" | "error" | "info") => void;
}

const VALID_TABS = new Set(TABS.map((t) => t.id));

export default function MainPanel({ showNotification }: Props) {
  const { activeTab: rawTab, setActiveTab } = useStore();
  const activeTab: Tab = VALID_TABS.has(rawTab as Tab) ? (rawTab as Tab) : "demo-guide";

  return (
    <main className="overflow-hidden flex flex-col bg-background">
      <div className="flex items-center gap-0 px-2 pt-0 pb-0 overflow-x-auto scrollbar-thin bg-card border-b">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "px-3 py-2 text-[12px] font-medium transition-colors whitespace-nowrap border-b-2 flex items-center gap-1.5",
              activeTab === tab.id
                ? "text-foreground border-b-primary bg-background"
                : "text-muted-foreground border-b-transparent hover:text-foreground/60 hover:bg-secondary",
              (tab.id === "demo-guide" || tab.id === "attack-lab") &&
                activeTab !== tab.id &&
                "text-primary/60",
            )}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      <ScrollArea className="flex-1">
        <div className="p-5">
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
      </ScrollArea>
    </main>
  );
}
