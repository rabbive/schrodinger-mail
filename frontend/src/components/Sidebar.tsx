import { useEffect } from "react";
import { useStore } from "@/hooks/useStore";
import { cn } from "@/lib/utils";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import {
  Inbox,
  Send,
  PenLine,
  Archive,
  Trash2,
  RefreshCw,
  ShieldCheck,
  ShieldAlert,
  KeyRound,
  Fingerprint,
} from "lucide-react";

const FOLDER_ICONS: Record<string, React.ReactNode> = {
  inbox: <Inbox className="w-3.5 h-3.5" />,
  sent: <Send className="w-3.5 h-3.5" />,
  drafts: <PenLine className="w-3.5 h-3.5" />,
  archive: <Archive className="w-3.5 h-3.5" />,
  trash: <Trash2 className="w-3.5 h-3.5" />,
};

export default function Sidebar() {
  const {
    activeUser,
    activeFolder,
    selectedEmailId,
    folders,
    emails,
    appState,
    loading,
    setActiveFolder,
    setSelectedEmailId,
    setActiveTab,
    loadFolders,
    receiveEmails,
  } = useStore();

  useEffect(() => {
    loadFolders();
  }, [activeUser, loadFolders]);

  const user = appState?.users[activeUser];

  return (
    <aside className="border-r bg-card flex flex-col max-lg:hidden">
      <div className="py-1.5">
        {folders.map((f) => (
          <button
            key={f.name}
            onClick={() => setActiveFolder(f.name)}
            className={cn(
              "w-full flex items-center gap-2 px-3 py-[6px] text-left text-[12px] font-medium transition-colors",
              f.name === activeFolder
                ? "bg-primary/10 text-primary border-l-2 border-l-primary"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground border-l-2 border-l-transparent",
            )}
          >
            <span className="w-4 text-center opacity-60">{FOLDER_ICONS[f.name] ?? <Archive className="w-3.5 h-3.5" />}</span>
            <span className="flex-1 capitalize">{f.name}</span>
            {f.unread > 0 && (
              <span className="min-w-[18px] h-[18px] flex items-center justify-center bg-primary text-primary-foreground text-[9px] font-bold rounded-full">
                {f.unread}
              </span>
            )}
          </button>
        ))}
      </div>

      <Separator className="mx-3" />

      {user && (
        <div className="px-3 py-2">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Fingerprint className="w-3 h-3 text-muted-foreground" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Key Fingerprints
            </span>
          </div>
          <div className="space-y-1">
            <div className="flex justify-between items-center">
              <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                <KeyRound className="w-2.5 h-2.5" /> KEM
              </span>
              <span className="font-mono text-[10px] text-quantum-blue">{user.kyber_fingerprint_short}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                <KeyRound className="w-2.5 h-2.5" /> SIG
              </span>
              <span className="font-mono text-[10px] text-quantum-green">{user.dilithium_fingerprint_short}</span>
            </div>
          </div>
        </div>
      )}

      <Separator className="mx-3" />

      <div className="px-3 py-2 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Messages
        </span>
        <div className="flex items-center gap-2">
          {loading && (
            <span className="flex items-center gap-1 text-[10px] text-primary">
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse-gentle" />
              Syncing
            </span>
          )}
          <Button variant="ghost" size="sm" onClick={receiveEmails} className="h-5 px-1.5 text-[10px]">
            <RefreshCw className="w-3 h-3" />
            Refresh
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1">
        {emails.length === 0 ? (
          <div className="px-3 py-8 text-center text-[11px] text-muted-foreground">
            No emails in {activeFolder}
          </div>
        ) : (
          [...emails].reverse().map((em) => (
            <EmailCard
              key={em.id}
              email={em}
              selected={selectedEmailId === em.id}
              onSelect={() => {
                setSelectedEmailId(em.id);
                setActiveTab("read");
              }}
            />
          ))
        )}
      </ScrollArea>
    </aside>
  );
}

function EmailCard({
  email,
  selected,
  onSelect,
}: {
  email: { id: number; sender: string; subject: string; read: boolean; verified: boolean; error?: string | null };
  selected: boolean;
  onSelect: () => void;
}) {
  const isUnread = !email.read;
  return (
    <div
      onClick={onSelect}
      className={cn(
        "px-3 py-2 cursor-pointer transition-colors border-l-2",
        selected
          ? "bg-primary/10 border-l-primary"
          : isUnread
            ? "bg-secondary/50 border-l-primary/50 hover:bg-secondary"
            : "border-l-transparent hover:bg-secondary",
      )}
    >
      <div className="flex items-center gap-1.5 text-[12px]">
        {isUnread && <span className="w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" />}
        <span className={cn("capitalize truncate", isUnread ? "font-semibold text-foreground" : "font-medium text-muted-foreground")}>
          {email.sender}
        </span>
        {email.verified ? (
          <Badge variant="success" className="ml-auto gap-1">
            <ShieldCheck className="w-2.5 h-2.5" />
            verified
          </Badge>
        ) : email.error ? (
          <Badge variant="destructive" className="ml-auto gap-1">
            <ShieldAlert className="w-2.5 h-2.5" />
            failed
          </Badge>
        ) : null}
      </div>
      <div className="text-[11px] text-muted-foreground mt-0.5 truncate">
        {email.subject || "(no subject)"}
      </div>
    </div>
  );
}
