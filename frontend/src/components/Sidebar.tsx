import { useEffect } from "react";
import { useStore } from "@/hooks/useStore";
import clsx from "clsx";

const FOLDER_ICONS: Record<string, string> = {
  inbox: "📥",
  sent: "📤",
  drafts: "📝",
  archive: "📦",
  trash: "🗑",
};

export default function Sidebar() {
  const {
    activeUser,
    activeFolder,
    selectedEmailId,
    folders,
    emails,
    appState,
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
      <div className="py-2">
        {folders.map((f) => (
          <button
            key={f.name}
            onClick={() => setActiveFolder(f.name)}
            className={clsx(
              "w-full flex items-center gap-2 px-3 py-1.5 text-left text-xs font-medium transition-colors",
              f.name === activeFolder
                ? "bg-accent/15 text-accent"
                : "text-[var(--text-dim)] hover:bg-[var(--surface2)]",
            )}
          >
            <span>{FOLDER_ICONS[f.name] ?? "📁"}</span>
            <span className="flex-1 capitalize">{f.name}</span>
            {f.unread > 0 && (
              <span className="min-w-[20px] h-5 flex items-center justify-center bg-accent text-white text-[10px] font-bold rounded-full">
                {f.unread}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="border-t border-[var(--border)] my-1" />

      {/* Key Info */}
      {user && (
        <div className="px-3 py-2">
          <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dim)] mb-1.5">
            Key Info
          </div>
          <div className="space-y-1 text-[11px]">
            <div className="flex justify-between">
              <span className="text-[var(--text-dim)]">Kyber PK</span>
              <span className="font-mono text-quantum-blue">{user.kyber_fingerprint_short}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--text-dim)]">Dilithium PK</span>
              <span className="font-mono text-quantum-green">{user.dilithium_fingerprint_short}</span>
            </div>
          </div>
        </div>
      )}

      <div className="border-t border-[var(--border)] my-1" />

      {/* Messages header with Check Mail */}
      <div className="px-3 py-2 flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dim)]">
          Messages
        </span>
        <button
          onClick={receiveEmails}
          className="text-[10px] font-semibold text-accent hover:text-accent-light transition-colors"
        >
          Check Mail
        </button>
      </div>

      {/* Email list */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {emails.length === 0 ? (
          <div className="px-3 py-6 text-center text-xs text-[var(--text-dim)]">
            No emails in {activeFolder}.
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
        "px-3 py-2 border-b border-[var(--border)] cursor-pointer hover:bg-[var(--surface2)] transition-colors",
        isUnread && "border-l-2 border-l-accent bg-accent/5",
        selected && "bg-accent/10 border-l-2 border-l-accent",
      )}
    >
      <div className="flex items-center gap-1.5 text-xs">
        {isUnread && <span className="w-1.5 h-1.5 rounded-full bg-accent flex-shrink-0" />}
        <span className="font-semibold capitalize">{email.sender}</span>
        {email.verified ? (
          <span className="ml-auto px-1.5 py-0.5 bg-quantum-green/15 text-quantum-green text-[9px] font-bold rounded">
            Verified
          </span>
        ) : email.error ? (
          <span className="ml-auto px-1.5 py-0.5 bg-quantum-red/15 text-quantum-red text-[9px] font-bold rounded">
            Failed
          </span>
        ) : null}
      </div>
      <div className="text-[11px] text-[var(--text-dim)] mt-0.5 truncate">
        {email.subject || "(no subject)"}
      </div>
    </div>
  );
}
