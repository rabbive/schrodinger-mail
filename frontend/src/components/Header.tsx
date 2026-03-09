import { useStore } from "@/hooks/useStore";
import clsx from "clsx";

export default function Header() {
  const { appState, activeUser, setActiveUser, toggleTheme, theme } = useStore();
  const users = appState ? Object.keys(appState.users) : [];

  return (
    <header className="col-span-full flex items-center gap-3 px-4 h-[48px] border-b border-[var(--border)] bg-[var(--surface)]">
      <div className="flex items-center gap-2.5">
        <span className="w-6 h-6 rounded bg-accent flex items-center justify-center text-white text-xs font-bold tracking-tight">
          S
        </span>
        <span className="font-semibold text-sm text-[var(--text)] tracking-tight">
          Schrödinger Mail
        </span>
      </div>

      <div className="h-4 w-px bg-[var(--border)] mx-1" />

      <div className="flex items-center gap-1.5">
        {appState && (
          <>
            <span className="px-1.5 py-0.5 bg-[var(--surface2)] text-[var(--text-dim)] text-[10px] font-mono font-medium rounded border border-[var(--border)]">
              {appState.kem_algorithm}
            </span>
            <span className="px-1.5 py-0.5 bg-[var(--surface2)] text-[var(--text-dim)] text-[10px] font-mono font-medium rounded border border-[var(--border)]">
              {appState.sig_algorithm}
            </span>
            <span className="px-1.5 py-0.5 bg-[var(--surface2)] text-[var(--text-dim)] text-[10px] font-mono font-medium rounded border border-[var(--border)]">
              AES-256-GCM
            </span>
          </>
        )}
      </div>

      <div className="flex-1" />

      <button
        onClick={toggleTheme}
        className="w-7 h-7 rounded bg-[var(--surface2)] border border-[var(--border)] flex items-center justify-center text-[11px] text-[var(--text-dim)] hover:text-[var(--text)] hover:border-[var(--border-light)] transition-colors"
        title="Toggle theme"
      >
        {theme === "dark" ? "☀" : "☾"}
      </button>

      <div className="h-4 w-px bg-[var(--border)] mx-0.5" />

      <div className="flex items-center gap-1">
        {users.map((name) => (
          <button
            key={name}
            onClick={() => setActiveUser(name)}
            className={clsx(
              "px-2.5 py-1 rounded text-xs font-medium transition-all",
              name === activeUser
                ? "bg-accent/15 text-accent border border-accent/30"
                : "bg-[var(--surface2)] text-[var(--text-dim)] border border-[var(--border)] hover:text-[var(--text)] hover:border-[var(--border-light)]",
            )}
          >
            {name.charAt(0).toUpperCase() + name.slice(1)}
          </button>
        ))}
      </div>
    </header>
  );
}
