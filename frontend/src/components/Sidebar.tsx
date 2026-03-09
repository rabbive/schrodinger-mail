import { useEffect } from "react";
import { useStore } from "@/hooks/useStore";
import clsx from "clsx";

const FOLDER_ICONS: Record<string, string> = {
  inbox: "↓",
  sent: "↑",
  drafts: "✎",
  archive: "▪",
  trash: "×",
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
    <aside className="border-r border-[var(--border)] bg-[var(--surface)] overflow-y-auto scrollbar-thin flex flex-col max-lg:hidden">
      {/* Folders */}
      <div className="py-1.5">
        {folders.map((f) => (
          <button
            key={f.name}
            onClick={() => setActiveFolder(f.name)}
            className={clsx(
              "w-full flex items-center gap-2 px-3 py-[6px] text-left text-[12px] font-medium transition-colors",
              f.name === activeFolder
                ? "bg-accent/10 text-accent border-l-2 border-l-accent"
                : "text-[var(--text-dim)] hover:bg-[var(--surface2)] hover:text-[var(--text)] border-l-2 border-l-transparent",
            )}
          >
            <span className="w-4 text-center text-[11px] opacity-60">{FOLDER_ICONS[f.name] ?? "·"}</span>
            <span className="flex-1 capitalize">{f.name}</span>
            {f.unread > 0 && (
              <span className="min-w-[18px] h-[18px] flex items-center justify-center bg-accent text-white text-[9px] font-bold rounded-full">
                {f.unread}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="border-t border-[var(--border)] mx-3 my-1" />

      {/* Key Info */}
      {user && (
        <div className="px-3 py-2">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-1.5">
            Key Fingerprints
          </div>
          <div className="space-y-1">
            <div className="flex justify-between items-center">
              <span className="text-[10px] text-[var(--text-dim)]">KEM</span>
              <span className="font-mono text-[10px] text-quantum-blue">{user.kyber_fingerprint_short}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[10px] text-[var(--text-dim)]">SIG</span>
              <span className="font-mono text-[10px] text-quantum-green">{user.dilithium_fingerprint_short}</span>
            </div>
          </div>
        </div>
      )}

      <div className="border-t border-[var(--border)] mx-3 my-1" />

      {/* Messages header */}
      <div className="px-3 py-2 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
          Messages
        </span>
        <div className="flex items-center gap-2">
          {loading && (
            <span className="flex items-center gap-1 text-[10px] text-accent">
              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-gentle" />
              Syncing
            </span>
          )}
          <button
            onClick={receiveEmails}
            className="text-[10px] font-medium text-[var(--text-dim)] hover:text-accent transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Email list */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {emails.length === 0 ? (
          <div className="px-3 py-8 text-center text-[11px] text-[var(--text-muted)]">
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
      </div>
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
      className={clsx(
        "px-3 py-2 cursor-pointer transition-colors border-l-2",
        selected
          ? "bg-accent/10 border-l-accent"
          : isUnread
            ? "bg-[var(--surface2)]/50 border-l-accent/50 hover:bg-[var(--surface2)]"
            : "border-l-transparent hover:bg-[var(--surface2)]",
      )}
    >
      <div className="flex items-center gap-1.5 text-[12px]">
        {isUnread && <span className="w-1.5 h-1.5 rounded-full bg-accent flex-shrink-0" />}
        <span className={clsx("capitalize truncate", isUnread ? "font-semibold text-[var(--text)]" : "font-medium text-[var(--text-dim)]")}>
          {email.sender}
        </span>
        {email.verified ? (
          <span className="ml-auto px-1 py-0.5 bg-quantum-green/10 text-quantum-green text-[9px] font-mono font-medium rounded">
            verified
          </span>
        ) : email.error ? (
          <span className="ml-auto px-1 py-0.5 bg-quantum-red/10 text-quantum-red text-[9px] font-mono font-medium rounded">
            failed
          </span>
        ) : null}
      </div>
      <div className="text-[11px] text-[var(--text-muted)] mt-0.5 truncate">
        {email.subject || "(no subject)"}
      </div>
    </div>
  );
}
