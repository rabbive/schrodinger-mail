import { useEffect, useState } from "react";
import { useStore } from "@/hooks/useStore";
import { api } from "@/services/api";

export default function SettingsPanel() {
  const { activeUser } = useStore();
  const [password, setPassword] = useState("");
  const [signature, setSignature] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getSettings(activeUser).then((d) => {
      const s = d.settings as Record<string, unknown>;
      setSignature(String(s.signature ?? ""));
    }).catch(console.error);
  }, [activeUser]);

  const savePassword = async () => {
    if (password.length < 4) return;
    await api.setPassword(activeUser, password);
    setPassword("");
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const saveSignature = async () => {
    await api.saveSettings(activeUser, { signature });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-lg space-y-6">
      <h2 className="text-base font-bold">Settings</h2>

      {saved && (
        <div className="text-xs text-quantum-green font-semibold">Saved successfully.</div>
      )}

      {/* Account */}
      <section className="space-y-2">
        <h3 className="text-sm font-semibold">Account</h3>
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded p-3 space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-[var(--text-dim)]">Username</span>
            <span className="font-semibold capitalize">{activeUser}</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="New password"
              className="flex-1 px-2 py-1.5 bg-[var(--bg)] border border-[var(--border)] rounded text-xs text-[var(--text)] focus:outline-none focus:border-accent"
            />
            <button
              onClick={savePassword}
              className="px-3 py-1.5 bg-accent text-white text-xs font-semibold rounded hover:bg-accent-light transition-colors"
            >
              Save
            </button>
          </div>
        </div>
      </section>

      {/* Signature */}
      <section className="space-y-2">
        <h3 className="text-sm font-semibold">Email Signature</h3>
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded p-3 space-y-2">
          <textarea
            value={signature}
            onChange={(e) => setSignature(e.target.value)}
            placeholder="Your email signature..."
            rows={3}
            className="w-full px-2 py-1.5 bg-[var(--bg)] border border-[var(--border)] rounded text-xs text-[var(--text)] focus:outline-none focus:border-accent resize-y"
          />
          <button
            onClick={saveSignature}
            className="px-3 py-1.5 bg-accent text-white text-xs font-semibold rounded hover:bg-accent-light transition-colors"
          >
            Save Signature
          </button>
        </div>
      </section>

      {/* Security Report */}
      <section className="space-y-2">
        <h3 className="text-sm font-semibold">Security Report</h3>
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded p-3">
          <p className="text-xs text-[var(--text-dim)] mb-2">
            Download a comprehensive HTML report of your security configuration.
          </p>
          <a
            href={`/api/report/${activeUser}`}
            className="inline-block px-3 py-1.5 bg-accent text-white text-xs font-semibold rounded hover:bg-accent-light transition-colors"
          >
            Download Report
          </a>
        </div>
      </section>

      {/* Demo Evidence Report */}
      <section className="space-y-2">
        <h3 className="text-sm font-semibold">Demo Evidence Report</h3>
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded p-3 space-y-2">
          <p className="text-xs text-[var(--text-dim)]">
            Export a comprehensive evidence bundle with algorithm details, attack outcomes, benchmarks,
            key fingerprints, and a full audit trail. Includes machine-readable JSON.
          </p>
          <a
            href={api.getDemoReportUrl(activeUser)}
            className="inline-block px-3 py-1.5 bg-quantum-green text-white text-xs font-semibold rounded hover:bg-quantum-green/80 transition-colors"
          >
            Export Demo Evidence
          </a>
        </div>
      </section>
    </div>
  );
}
