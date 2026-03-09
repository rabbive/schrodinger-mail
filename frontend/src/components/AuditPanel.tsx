import { useEffect, useState } from "react";
import { useStore } from "@/hooks/useStore";
import { api } from "@/services/api";
import type { AuditEntry } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ClipboardList, RefreshCw } from "lucide-react";

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
    <div className="max-w-2xl space-y-3">
      <div className="flex items-center gap-2">
        <ClipboardList className="w-4 h-4 text-primary" />
        <h2 className="text-base font-bold">Security Audit Log</h2>
      </div>

      <Button variant="secondary" size="sm" onClick={load}>
        <RefreshCw className="w-3.5 h-3.5" /> Refresh
      </Button>

      {entries.length === 0 ? (
        <div className="text-sm text-muted-foreground">No audit entries.</div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-secondary">
                  <th className="text-left px-3 py-2 font-semibold">Action</th>
                  <th className="text-left px-3 py-2 font-semibold">Details</th>
                  <th className="text-left px-3 py-2 font-semibold">IP</th>
                  <th className="text-left px-3 py-2 font-semibold">Time</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id} className="border-t">
                    <td className="px-3 py-1.5 font-semibold">{e.action}</td>
                    <td className="px-3 py-1.5 text-muted-foreground max-w-[200px] truncate">
                      {e.details}
                    </td>
                    <td className="px-3 py-1.5 font-mono text-muted-foreground">{e.ip_address}</td>
                    <td className="px-3 py-1.5 text-muted-foreground">{e.timestamp}</td>
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
