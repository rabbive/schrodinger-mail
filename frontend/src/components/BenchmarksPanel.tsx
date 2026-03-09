import { useState } from "react";
import { api } from "@/services/api";
import type { BenchmarkResult } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Gauge, Play, Loader2 } from "lucide-react";

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
    <div className="max-w-xl space-y-3">
      <div className="flex items-center gap-2">
        <Gauge className="w-4 h-4 text-primary" />
        <h2 className="text-base font-bold">Cryptographic Benchmarks</h2>
      </div>
      <p className="text-xs text-muted-foreground">Average of 5 iterations per operation.</p>

      <Button onClick={run} disabled={loading}>
        {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
        {loading ? "Running..." : "Run Benchmarks"}
      </Button>

      {results && (
        <Card>
          <CardContent className="p-0">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-secondary">
                  <th className="text-left px-3 py-2 font-semibold">Operation</th>
                  <th className="text-right px-3 py-2 font-semibold">Avg (ms)</th>
                  <th className="text-right px-3 py-2 font-semibold">Output (bytes)</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r) => (
                  <tr key={r.operation} className="border-t">
                    <td className="px-3 py-1.5">{r.operation}</td>
                    <td className="px-3 py-1.5 text-right font-mono text-quantum-green">
                      {r.avg_ms.toFixed(3)}
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono text-muted-foreground">
                      {r.size_bytes.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
