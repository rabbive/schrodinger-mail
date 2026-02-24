import { useEffect, useState } from "react";
import { useStore } from "@/hooks/useStore";
import { api } from "@/services/api";
import type { AuditEntry } from "@/types";

export default function AuditPanel() {
  const { activeUser } = useStore();
  const [entries, setEntries] = useState<AuditEntry[]>([]);

  const load = () => {
    api.getAuditLog(activeUser).then((d) => setEntries(d.log)).catch(console.error);
  };

  useEffect(() => {
    load();
  }, [activeUser]);

  return (
    <div className="max-w-2xl">
      <h2 className="text-base font-bold mb-3">Security Audit Log</h2>
      <button
        onClick={load}
        className="px-3 py-1.5 bg-[var(--surface2)] text-xs font-medium rounded hover:bg-[var(--border)] transition-colors mb-3"
      >
        Refresh
      </button>

      {entries.length === 0 ? (
        <div className="text-sm text-[var(--text-dim)]">No audit entries.</div>
      ) : (
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-[var(--surface2)]">
                <th className="text-left px-3 py-2 font-semibold">Action</th>
                <th className="text-left px-3 py-2 font-semibold">Details</th>
                <th className="text-left px-3 py-2 font-semibold">IP</th>
                <th className="text-left px-3 py-2 font-semibold">Time</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id} className="border-t border-[var(--border)]">
                  <td className="px-3 py-1.5 font-semibold">{e.action}</td>
                  <td className="px-3 py-1.5 text-[var(--text-dim)] max-w-[200px] truncate">
                    {e.details}
                  </td>
                  <td className="px-3 py-1.5 font-mono text-[var(--text-dim)]">{e.ip_address}</td>
                  <td className="px-3 py-1.5 text-[var(--text-dim)]">{e.timestamp}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
