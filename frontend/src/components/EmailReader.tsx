import { useEffect, useState } from "react";
import { useStore } from "@/hooks/useStore";
import { cn } from "@/lib/utils";
import { api } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Mail,
  Reply,
  Forward,
  Archive,
  Trash2,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  RefreshCcwDot,
  Check,
  X,
  Code,
  Loader2,
} from "lucide-react";

interface VerifyCheck {
  check: string;
  status: string;
  detail: string;
}

interface VerifyDetails {
  email_id: number;
  verified: boolean;
  error: string | null;
  sender: string;
  message_id: string | null;
  timestamp: string | null;
  algorithms: { kem: string; sig: string; dem: string };
  key_sizes: Record<string, number>;
  sender_fingerprints: Record<string, string>;
  replay_cache_hit: boolean;
  checks: VerifyCheck[];
}

export default function EmailReader() {
  const { emails, selectedEmailId, activeUser } = useStore();
  const [details, setDetails] = useState<VerifyDetails | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [showJson, setShowJson] = useState(false);

  const selected = emails.find((e) => e.id === selectedEmailId);

  useEffect(() => {
    if (!selected) {
      setDetails(null);
      return;
    }
    setLoadingDetails(true);
    api
      .getVerifyDetails(activeUser, selected.id)
      .then((d) => setDetails(d))
      .catch(() => setDetails(null))
      .finally(() => setLoadingDetails(false));
  }, [selected?.id, activeUser]);

  if (!selected) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
        <div className="w-10 h-10 rounded-lg bg-secondary border flex items-center justify-center mb-3">
          <Mail className="w-5 h-5" />
        </div>
        <div className="text-[12px]">Select an email from the sidebar to read it.</div>
      </div>
    );
  }

  const getVerificationBadge = () => {
    if (selected.verified) {
      return (
        <Badge variant="success" className="gap-1">
          <ShieldCheck className="w-3 h-3" /> verified
        </Badge>
      );
    }
    const errorText = selected.error?.toLowerCase() ?? "";
    let label = "unverified";
    let Icon = ShieldAlert;
    if (errorText.includes("tamper")) { label = "tampered"; Icon = ShieldX; }
    else if (errorText.includes("signature")) { label = "forged"; Icon = ShieldX; }
    else if (errorText.includes("replay")) { label = "replay"; Icon = RefreshCcwDot; }
    return (
      <Badge variant="destructive" className="gap-1">
        <Icon className="w-3 h-3" /> {label}
      </Badge>
    );
  };

  const bodyText = selected.plaintext
    ? extractBody(selected.plaintext)
    : "(Unable to decrypt)";

  return (
    <div className="max-w-2xl space-y-4">
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-base font-semibold text-foreground">
            {selected.subject || "(no subject)"}
          </span>
          {getVerificationBadge()}
        </div>
        <div className="text-[12px] text-muted-foreground space-y-0.5">
          <div>
            From:{" "}
            <span className="font-medium capitalize text-foreground">
              {selected.sender}
            </span>
          </div>
          {selected.thread_id && (
            <div>
              Thread:{" "}
              <span className="font-mono text-primary text-[11px]">
                {selected.thread_id.slice(0, 8)}...
              </span>
            </div>
          )}
          <div className="text-muted-foreground">{selected.timestamp}</div>
        </div>
      </div>

      {selected.error && (
        <div className="p-3 bg-destructive/8 border border-destructive/20 rounded-md text-[12px] text-destructive flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 flex-shrink-0" />
          {selected.error}
        </div>
      )}

      <Card>
        <CardContent className="p-4">
          <div className="text-[13px] whitespace-pre-wrap leading-relaxed font-mono text-foreground">
            {bodyText}
          </div>
        </CardContent>
      </Card>

      <div className="flex gap-2">
        <Button size="sm">
          <Reply className="w-3.5 h-3.5" /> Reply
        </Button>
        <Button variant="secondary" size="sm">
          <Forward className="w-3.5 h-3.5" /> Forward
        </Button>
        <Button variant="secondary" size="sm">
          <Archive className="w-3.5 h-3.5" /> Archive
        </Button>
        <Button variant="destructive" size="sm">
          <Trash2 className="w-3.5 h-3.5" /> Delete
        </Button>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between py-2 px-3">
          <CardTitle className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Verification Evidence
          </CardTitle>
          {details && (
            <Button variant="ghost" size="sm" onClick={() => setShowJson(!showJson)} className="h-5 px-1.5 text-[10px]">
              <Code className="w-3 h-3" />
              {showJson ? "Hide JSON" : "Show JSON"}
            </Button>
          )}
        </CardHeader>

        <CardContent className="p-3 pt-0">
          {loadingDetails ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="w-4 h-4 text-primary animate-spin" />
            </div>
          ) : details ? (
            <div className="space-y-3">
              <div className="space-y-1">
                {details.checks.map((check, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2 px-2.5 py-1.5 rounded-md bg-background border"
                  >
                    <span
                      className={cn(
                        "w-4 h-4 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5",
                        check.status === "pass"
                          ? "bg-quantum-green/15 text-quantum-green"
                          : "bg-destructive/15 text-destructive",
                      )}
                    >
                      {check.status === "pass" ? <Check className="w-2.5 h-2.5" /> : <X className="w-2.5 h-2.5" />}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="text-[11px] font-medium text-foreground">
                        {check.check}
                      </div>
                      <div className="text-[10px] text-muted-foreground mt-0.5 leading-snug">
                        {check.detail}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-2">
                <MetaCard label="KEM Algorithm" value={details.algorithms.kem} />
                <MetaCard label="Signature" value={details.algorithms.sig} />
                <MetaCard label="Symmetric" value={details.algorithms.dem} />
                <MetaCard
                  label="Message-ID"
                  value={details.message_id?.slice(0, 20) || "N/A"}
                  mono
                />
                {details.sender_fingerprints.kyber && (
                  <MetaCard
                    label="Sender Kyber FP"
                    value={details.sender_fingerprints.kyber.slice(0, 24) + "..."}
                    mono
                  />
                )}
                {details.sender_fingerprints.dilithium && (
                  <MetaCard
                    label="Sender Dilithium FP"
                    value={details.sender_fingerprints.dilithium.slice(0, 24) + "..."}
                    mono
                  />
                )}
                <MetaCard
                  label="Replay Cache"
                  value={details.replay_cache_hit ? "HIT (duplicate)" : "MISS (unique)"}
                />
                <MetaCard
                  label="Key Sizes"
                  value={`KEM PK: ${details.key_sizes.kyber_pk}B | SIG PK: ${details.key_sizes.dilithium_pk}B`}
                  mono
                />
              </div>

              {showJson && (
                <div className="mt-2">
                  <pre className="p-3 bg-background border rounded-md text-[10px] font-mono text-muted-foreground overflow-x-auto max-h-60 scrollbar-thin">
                    {JSON.stringify(details, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 text-center text-[11px] text-muted-foreground">
              Verification data unavailable.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function MetaCard({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="px-2.5 py-1.5 rounded-md bg-background border">
      <div className="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div
        className={cn(
          "text-[11px] text-primary mt-0.5 break-all leading-snug",
          mono && "font-mono",
        )}
      >
        {value}
      </div>
    </div>
  );
}

function extractBody(plaintext: string): string {
  const lines = plaintext.split("\n");
  let bodyStart = 0;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i] === "") {
      bodyStart = i + 1;
      break;
    }
  }
  return lines.slice(bodyStart).join("\n").trim();
}
