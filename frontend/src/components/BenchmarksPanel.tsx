import { useState } from "react";
import { api } from "@/services/api";
import type { BenchmarkResult } from "@/types";

export default function BenchmarksPanel() {
  const [results, setResults] = useState<BenchmarkResult[] | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    try {
      const data = await api.getBenchmarks();
      setResults(data.benchmarks);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-xl">
      <h2 className="text-base font-bold mb-1">Cryptographic Benchmarks</h2>
      <p className="text-xs text-[var(--text-dim)] mb-3">Average of 5 iterations per operation.</p>
      <button
        onClick={run}
        disabled={loading}
        className="px-4 py-2 bg-accent text-white text-sm font-semibold rounded hover:bg-accent-light transition-colors disabled:opacity-50"
      >
        {loading ? "Running..." : "Run Benchmarks"}
      </button>

      {results && (
        <div className="mt-4 bg-[var(--surface)] border border-[var(--border)] rounded overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-[var(--surface2)]">
                <th className="text-left px-3 py-2 font-semibold">Operation</th>
                <th className="text-right px-3 py-2 font-semibold">Avg (ms)</th>
                <th className="text-right px-3 py-2 font-semibold">Output (bytes)</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.operation} className="border-t border-[var(--border)]">
                  <td className="px-3 py-1.5">{r.operation}</td>
                  <td className="px-3 py-1.5 text-right font-mono text-quantum-green">
                    {r.avg_ms.toFixed(3)}
                  </td>
                  <td className="px-3 py-1.5 text-right font-mono text-[var(--text-dim)]">
                    {r.size_bytes.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
