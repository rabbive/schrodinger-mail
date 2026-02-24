import { useEffect, useState } from "react";
import { useStore } from "@/hooks/useStore";
import { api } from "@/services/api";

export default function KeysPanel() {
  const { activeUser } = useStore();
  const [keys, setKeys] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api.getKeys(activeUser).then(setKeys).catch(console.error);
  }, [activeUser]);

  if (!keys) return <div className="text-sm text-[var(--text-dim)]">Loading keys...</div>;

  const rows = [
    ["KEM Algorithm", keys.kem_algorithm],
    ["SIG Algorithm", keys.sig_algorithm],
    ["Kyber PK Size", `${keys.kyber_pk_bytes} bytes`],
    ["Kyber SK Size", `${keys.kyber_sk_bytes} bytes`],
    ["Dilithium PK Size", `${keys.dilithium_pk_bytes} bytes`],
    ["Dilithium SK Size", `${keys.dilithium_sk_bytes} bytes`],
  ];

  return (
    <div className="max-w-xl">
      <h2 className="text-base font-bold mb-3">Key Management</h2>

      <div className="bg-[var(--surface)] border border-[var(--border)] rounded overflow-hidden">
        <table className="w-full text-sm">
          <tbody>
            {rows.map(([label, value]) => (
              <tr key={String(label)} className="border-b border-[var(--border)] last:border-b-0">
                <td className="px-3 py-2 text-[var(--text-dim)] text-xs font-medium">{String(label)}</td>
                <td className="px-3 py-2 font-mono text-xs">{String(value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 space-y-2">
        <h3 className="text-sm font-semibold">Fingerprints</h3>
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded p-3 text-xs font-mono space-y-1.5">
          <div>
            <span className="text-[var(--text-dim)]">Kyber: </span>
            <span className="text-quantum-blue break-all">{String(keys.kyber_pk_fingerprint)}</span>
          </div>
          <div>
            <span className="text-[var(--text-dim)]">Dilithium: </span>
            <span className="text-quantum-green break-all">{String(keys.dilithium_pk_fingerprint)}</span>
          </div>
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        <a
          href={`/api/keys/export/${activeUser}/kyber_pk`}
          className="px-3 py-1.5 bg-[var(--surface2)] text-xs font-medium rounded hover:bg-[var(--border)] transition-colors"
        >
          Export Kyber PK
        </a>
        <a
          href={`/api/keys/export/${activeUser}/dilithium_pk`}
          className="px-3 py-1.5 bg-[var(--surface2)] text-xs font-medium rounded hover:bg-[var(--border)] transition-colors"
        >
          Export Dilithium PK
        </a>
      </div>
    </div>
  );
}
