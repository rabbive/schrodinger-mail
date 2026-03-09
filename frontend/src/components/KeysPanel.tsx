import { useEffect, useState } from "react";
import { useStore } from "@/hooks/useStore";
import { api } from "@/services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { KeyRound, Download, Fingerprint, Loader2 } from "lucide-react";

export default function KeysPanel() {
  const { activeUser } = useStore();
  const [keys, setKeys] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api.getKeys(activeUser).then(setKeys).catch(console.error);
  }, [activeUser]);

  if (!keys) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin" /> Loading keys...
      </div>
    );
  }

  const rows = [
    ["KEM Algorithm", keys.kem_algorithm],
    ["SIG Algorithm", keys.sig_algorithm],
    ["Kyber PK Size", `${keys.kyber_pk_bytes} bytes`],
    ["Kyber SK Size", `${keys.kyber_sk_bytes} bytes`],
    ["Dilithium PK Size", `${keys.dilithium_pk_bytes} bytes`],
    ["Dilithium SK Size", `${keys.dilithium_sk_bytes} bytes`],
  ];

  return (
    <div className="max-w-xl space-y-4">
      <div className="flex items-center gap-2">
        <KeyRound className="w-4 h-4 text-primary" />
        <h2 className="text-base font-bold">Key Management</h2>
      </div>

      <Card>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <tbody>
              {rows.map(([label, value]) => (
                <tr key={String(label)} className="border-b last:border-b-0">
                  <td className="px-3 py-2 text-muted-foreground text-xs font-medium">{String(label)}</td>
                  <td className="px-3 py-2 font-mono text-xs">{String(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-1.5">
            <Fingerprint className="w-3.5 h-3.5 text-primary" />
            Fingerprints
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs font-mono space-y-1.5">
          <div>
            <span className="text-muted-foreground">Kyber: </span>
            <span className="text-quantum-blue break-all">{String(keys.kyber_pk_fingerprint)}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Dilithium: </span>
            <span className="text-quantum-green break-all">{String(keys.dilithium_pk_fingerprint)}</span>
          </div>
        </CardContent>
      </Card>

      <div className="flex gap-2">
        <Button variant="secondary" size="sm" asChild>
          <a href={`/api/keys/export/${activeUser}/kyber_pk`}>
            <Download className="w-3.5 h-3.5" /> Export Kyber PK
          </a>
        </Button>
        <Button variant="secondary" size="sm" asChild>
          <a href={`/api/keys/export/${activeUser}/dilithium_pk`}>
            <Download className="w-3.5 h-3.5" /> Export Dilithium PK
          </a>
        </Button>
      </div>
    </div>
  );
}
