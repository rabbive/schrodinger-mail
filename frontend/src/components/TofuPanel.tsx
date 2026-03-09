import { useEffect, useState } from "react";
import { useStore } from "@/hooks/useStore";
import { api } from "@/services/api";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  AlertTriangle,
  RotateCcw,
  Check,
  X,
  Loader2,
  Fingerprint,
  KeyRound,
} from "lucide-react";

interface FingerprintState {
  username: string;
  kyber: string;
  dilithium: string;
}

interface RotationRecord {
  username: string;
  old: { kyber: string; dilithium: string };
  current: { kyber: string; dilithium: string };
  timestamp: string;
  accepted: boolean;
}

export default function TofuPanel() {
  const { appState, activeUser, addCryptoSteps, clearCryptoLog, init } = useStore();
  const [fingerprints, setFingerprints] = useState<FingerprintState[]>([]);
  const [loading, setLoading] = useState(false);
  const [rotating, setRotating] = useState<string | null>(null);
  const [rotationHistory, setRotationHistory] = useState<RotationRecord[]>([]);
  const [pendingWarning, setPendingWarning] = useState<RotationRecord | null>(null);

  const users = appState ? Object.keys(appState.users) : [];

  const loadFingerprints = async () => {
    setLoading(true);
    try {
      const results: FingerprintState[] = [];
      for (const user of users) {
        const data = await api.getKeys(user);
        results.push({
          username: user,
          kyber: (data.kyber_pk_fingerprint as string) || "",
          dilithium: (data.dilithium_pk_fingerprint as string) || "",
        });
      }
      setFingerprints(results);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFingerprints();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeUser, users.length]);

  const handleRotate = async (username: string) => {
    if (rotating) return;
    setRotating(username);
    clearCryptoLog();

    try {
      const result = await api.rotateKeys(username);
      addCryptoSteps(result.steps);

      const record: RotationRecord = {
        username,
        old: result.old_fingerprints as { kyber: string; dilithium: string },
        current: result.new_fingerprints as { kyber: string; dilithium: string },
        timestamp: new Date().toISOString(),
        accepted: false,
      };

      setPendingWarning(record);
      await loadFingerprints();
      await init();
    } catch (err) {
      console.error("Key rotation failed:", err);
    } finally {
      setRotating(null);
    }
  };

  const acceptRotation = () => {
    if (pendingWarning) {
      setRotationHistory((prev) => [
        { ...pendingWarning, accepted: true },
        ...prev,
      ]);
      setPendingWarning(null);
    }
  };

  const rejectRotation = () => {
    if (pendingWarning) {
      setRotationHistory((prev) => [
        { ...pendingWarning, accepted: false },
        ...prev,
      ]);
      setPendingWarning(null);
    }
  };

  const trustState = (username: string) => {
    const hasHistory = rotationHistory.some((r) => r.username === username);
    const hasPending = pendingWarning?.username === username;
    if (hasPending) return "warning";
    if (hasHistory) {
      const latest = rotationHistory.find((r) => r.username === username);
      return latest?.accepted ? "rotated" : "rejected";
    }
    return "trusted";
  };

  const trustBadge = (state: string) => {
    switch (state) {
      case "trusted":
        return { label: "Trusted (TOFU)", variant: "success" as const, icon: ShieldCheck };
      case "rotated":
        return { label: "Rotated (Accepted)", variant: "default" as const, icon: RotateCcw };
      case "warning":
        return { label: "Key Changed!", variant: "warning" as const, icon: AlertTriangle };
      case "rejected":
        return { label: "Rejected", variant: "destructive" as const, icon: ShieldX };
      default:
        return { label: "Unknown", variant: "outline" as const, icon: ShieldAlert };
    }
  };

  return (
    <div className="max-w-3xl space-y-5">
      <div className="flex items-center gap-2">
        <ShieldCheck className="w-4 h-4 text-primary" />
        <div>
          <h2 className="text-[14px] font-semibold text-foreground">
            Trust & Key Rotation (TOFU)
          </h2>
          <p className="text-[11px] text-muted-foreground mt-1">
            Trust-On-First-Use key management. View fingerprints, simulate key rotation, and observe trust warnings.
          </p>
        </div>
      </div>

      {pendingWarning && (
        <div className="p-4 rounded-md border-2 border-quantum-orange bg-quantum-orange/5 animate-fade-slide">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-5 h-5 text-quantum-orange" />
            <span className="text-[13px] font-bold text-quantum-orange">
              Key Fingerprint Changed — Possible MITM Attack
            </span>
          </div>
          <p className="text-[12px] text-foreground mb-3 leading-relaxed">
            The public key fingerprint for <span className="font-semibold capitalize">{pendingWarning.username}</span> has
            changed. This could indicate a legitimate key rotation or a man-in-the-middle attack where an attacker
            has substituted their own public key.
          </p>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div className="p-2.5 rounded-md bg-destructive/8 border border-destructive/15">
              <div className="text-[9px] font-semibold uppercase tracking-wider text-destructive mb-1 flex items-center gap-1">
                <X className="w-2.5 h-2.5" /> Previous Kyber Fingerprint
              </div>
              <div className="text-[10px] font-mono text-muted-foreground break-all leading-relaxed">
                {pendingWarning.old.kyber}
              </div>
            </div>
            <div className="p-2.5 rounded-md bg-quantum-green/8 border border-quantum-green/15">
              <div className="text-[9px] font-semibold uppercase tracking-wider text-quantum-green mb-1 flex items-center gap-1">
                <Check className="w-2.5 h-2.5" /> New Kyber Fingerprint
              </div>
              <div className="text-[10px] font-mono text-muted-foreground break-all leading-relaxed">
                {pendingWarning.current.kyber}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div className="p-2.5 rounded-md bg-destructive/8 border border-destructive/15">
              <div className="text-[9px] font-semibold uppercase tracking-wider text-destructive mb-1 flex items-center gap-1">
                <X className="w-2.5 h-2.5" /> Previous Dilithium Fingerprint
              </div>
              <div className="text-[10px] font-mono text-muted-foreground break-all leading-relaxed">
                {pendingWarning.old.dilithium}
              </div>
            </div>
            <div className="p-2.5 rounded-md bg-quantum-green/8 border border-quantum-green/15">
              <div className="text-[9px] font-semibold uppercase tracking-wider text-quantum-green mb-1 flex items-center gap-1">
                <Check className="w-2.5 h-2.5" /> New Dilithium Fingerprint
              </div>
              <div className="text-[10px] font-mono text-muted-foreground break-all leading-relaxed">
                {pendingWarning.current.dilithium}
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <Button onClick={acceptRotation} className="bg-quantum-green text-white hover:bg-quantum-green/90" size="sm">
              <Check className="w-3.5 h-3.5" /> Accept New Key
            </Button>
            <Button onClick={rejectRotation} variant="destructive" size="sm">
              <X className="w-3.5 h-3.5" /> Reject (Possible MITM)
            </Button>
          </div>
        </div>
      )}

      <div className="space-y-2">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <Fingerprint className="w-3 h-3" />
          User Fingerprints & Trust States
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 text-primary animate-spin" />
          </div>
        ) : (
          <div className="space-y-2">
            {fingerprints.map((fp) => {
              const state = trustState(fp.username);
              const badge = trustBadge(state);
              const isRotating = rotating === fp.username;
              const BadgeIcon = badge.icon;

              return (
                <Card key={fp.username} className="overflow-hidden">
                  <div className="flex items-center gap-3 px-4 py-3">
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <span className="text-[13px] font-bold text-primary capitalize">
                        {fp.username.charAt(0)}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[13px] font-semibold text-foreground capitalize">
                          {fp.username}
                        </span>
                        <Badge variant={badge.variant} className="gap-1">
                          <BadgeIcon className="w-2.5 h-2.5" /> {badge.label}
                        </Badge>
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleRotate(fp.username)}
                      disabled={!!rotating}
                      className={cn(
                        isRotating && "text-quantum-orange border-quantum-orange/20",
                      )}
                    >
                      {isRotating ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <RotateCcw className="w-3.5 h-3.5" />
                      )}
                      {isRotating ? "Rotating..." : "Rotate Keys"}
                    </Button>
                  </div>

                  <CardContent className="px-4 pb-3 pt-0 space-y-1.5">
                    <FingerprintRow label="Kyber768 (KEM)" value={fp.kyber} />
                    <FingerprintRow label="Dilithium3 (SIG)" value={fp.dilithium} />
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {rotationHistory.length > 0 && (
        <div className="space-y-2">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
            <RotateCcw className="w-3 h-3" /> Rotation History
          </div>
          <Card className="overflow-hidden">
            {rotationHistory.map((record, i) => (
              <div
                key={i}
                className={cn(
                  "flex items-center gap-3 px-3 py-2",
                  i < rotationHistory.length - 1 && "border-b",
                )}
              >
                <span
                  className={cn(
                    "w-2 h-2 rounded-full flex-shrink-0",
                    record.accepted ? "bg-quantum-green" : "bg-destructive",
                  )}
                />
                <div className="flex-1 min-w-0">
                  <span className="text-[11px] font-medium text-foreground capitalize">
                    {record.username}
                  </span>
                  <span className="text-[10px] text-muted-foreground ml-2">
                    {record.accepted ? "Key accepted" : "Key rejected (MITM warning)"}
                  </span>
                </div>
                <span className="text-[9px] font-mono text-muted-foreground">
                  {new Date(record.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </Card>
        </div>
      )}

      <Card className="p-3 text-[11px] text-muted-foreground space-y-1.5">
        <div className="font-medium text-foreground/70 text-[12px] flex items-center gap-1.5">
          <KeyRound className="w-3 h-3" /> About Trust-On-First-Use (TOFU)
        </div>
        <p>
          TOFU means the first time you see a user's public key, you trust it. If the fingerprint ever changes,
          a warning is raised because it could mean a man-in-the-middle has substituted their own key.
        </p>
        <p>
          This is the same model used by SSH (<span className="font-mono text-primary">known_hosts</span>) and
          Signal's safety numbers. In production, you'd verify fingerprints out-of-band (QR code, phone call).
        </p>
      </Card>
    </div>
  );
}

function FingerprintRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-[10px] font-medium text-muted-foreground w-28 flex-shrink-0 pt-0.5 flex items-center gap-1">
        <Fingerprint className="w-2.5 h-2.5" /> {label}
      </span>
      <span className="text-[10px] font-mono text-primary break-all leading-relaxed">
        {value || "N/A"}
      </span>
    </div>
  );
}
