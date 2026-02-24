import { useStore } from "@/hooks/useStore";
import clsx from "clsx";

export default function Header() {
  const { appState, activeUser, setActiveUser, toggleTheme } = useStore();
  const users = appState ? Object.keys(appState.users) : [];

  return (
    <header className="col-span-full flex items-center gap-3 px-4 border-b border-[var(--border)] bg-[var(--surface)]">
      <div className="flex items-center gap-2 font-bold text-lg">
        <span className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center text-white text-sm font-bold">
          Q
        </span>
        <span className="text-[var(--text)]">uantum Mail</span>
      </div>

      <div className="flex items-center gap-1.5 ml-3">
        {appState && (
          <>
            <span className="px-2 py-0.5 bg-accent/15 text-accent text-[10px] font-bold rounded">
              KEM: {appState.kem_algorithm}
            </span>
            <span className="px-2 py-0.5 bg-quantum-green/15 text-quantum-green text-[10px] font-bold rounded">
              SIG: {appState.sig_algorithm}
            </span>
            <span className="px-2 py-0.5 bg-quantum-blue/15 text-quantum-blue text-[10px] font-bold rounded">
              DEM: AES-256-GCM
            </span>
          </>
        )}
      </div>

      <div className="flex-1" />

      <button
        onClick={toggleTheme}
        className="w-8 h-8 rounded-lg bg-[var(--surface2)] flex items-center justify-center text-sm hover:bg-[var(--border)] transition-colors"
        title="Toggle theme"
      >
        🌓
      </button>

      <div className="flex items-center gap-1">
        {users.map((name) => (
          <button
            key={name}
            onClick={() => setActiveUser(name)}
            className={clsx(
              "px-3 py-1 rounded text-xs font-semibold transition-colors",
              name === activeUser
                ? "bg-accent text-white"
                : "bg-[var(--surface2)] text-[var(--text-dim)] hover:bg-[var(--border)]",
            )}
          >
            {name.charAt(0).toUpperCase() + name.slice(1)}
          </button>
        ))}
      </div>
    </header>
  );
}
