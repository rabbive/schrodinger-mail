import { useEffect, useState } from "react";
import { useStore } from "@/hooks/useStore";
import { api } from "@/services/api";
import clsx from "clsx";

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
        return { label: "Trusted (TOFU)", class: "bg-quantum-green/10 text-quantum-green border-quantum-green/20" };
      case "rotated":
        return { label: "Rotated (Accepted)", class: "bg-accent/10 text-accent border-accent/20" };
      case "warning":
        return { label: "Key Changed!", class: "bg-quantum-orange/10 text-quantum-orange border-quantum-orange/20" };
      case "rejected":
        return { label: "Rejected", class: "bg-quantum-red/10 text-quantum-red border-quantum-red/20" };
      default:
        return { label: "Unknown", class: "bg-[var(--surface2)] text-[var(--text-muted)] border-[var(--border)]" };
    }
  };

  return (
    <div className="max-w-3xl space-y-5">
      <div>
        <h2 className="text-[14px] font-semibold text-[var(--text)]">
          Trust & Key Rotation (TOFU)
        </h2>
        <p className="text-[11px] text-[var(--text-muted)] mt-1">
          Trust-On-First-Use key management. View fingerprints, simulate key rotation, and observe trust warnings.
        </p>
      </div>

      {/* MITM Warning Banner */}
      {pendingWarning && (
        <div className="p-4 rounded border-2 border-quantum-orange bg-quantum-orange/5 animate-fade-slide">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">⚠</span>
            <span className="text-[13px] font-bold text-quantum-orange">
              Key Fingerprint Changed — Possible MITM Attack
            </span>
          </div>
          <p className="text-[12px] text-[var(--text)] mb-3 leading-relaxed">
            The public key fingerprint for <span className="font-semibold capitalize">{pendingWarning.username}</span> has
            changed. This could indicate a legitimate key rotation or a man-in-the-middle attack where an attacker
            has substituted their own public key.
          </p>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div className="p-2.5 rounded bg-quantum-red/8 border border-quantum-red/15">
              <div className="text-[9px] font-semibold uppercase tracking-wider text-quantum-red mb-1">
                Previous Kyber Fingerprint
              </div>
              <div className="text-[10px] font-mono text-[var(--text-dim)] break-all leading-relaxed">
                {pendingWarning.old.kyber}
              </div>
            </div>
            <div className="p-2.5 rounded bg-quantum-green/8 border border-quantum-green/15">
              <div className="text-[9px] font-semibold uppercase tracking-wider text-quantum-green mb-1">
                New Kyber Fingerprint
              </div>
              <div className="text-[10px] font-mono text-[var(--text-dim)] break-all leading-relaxed">
                {pendingWarning.current.kyber}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div className="p-2.5 rounded bg-quantum-red/8 border border-quantum-red/15">
              <div className="text-[9px] font-semibold uppercase tracking-wider text-quantum-red mb-1">
                Previous Dilithium Fingerprint
              </div>
              <div className="text-[10px] font-mono text-[var(--text-dim)] break-all leading-relaxed">
                {pendingWarning.old.dilithium}
              </div>
            </div>
            <div className="p-2.5 rounded bg-quantum-green/8 border border-quantum-green/15">
              <div className="text-[9px] font-semibold uppercase tracking-wider text-quantum-green mb-1">
                New Dilithium Fingerprint
              </div>
              <div className="text-[10px] font-mono text-[var(--text-dim)] break-all leading-relaxed">
                {pendingWarning.current.dilithium}
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={acceptRotation}
              className="px-4 py-1.5 bg-quantum-green text-white text-[12px] font-semibold rounded hover:bg-quantum-green/80 transition-colors"
            >
              Accept New Key
            </button>
            <button
              onClick={rejectRotation}
              className="px-4 py-1.5 bg-quantum-red text-white text-[12px] font-semibold rounded hover:bg-quantum-red/80 transition-colors"
            >
              Reject (Possible MITM)
            </button>
          </div>
        </div>
      )}

      {/* User fingerprints */}
      <div className="space-y-2">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
          User Fingerprints & Trust States
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="space-y-2">
            {fingerprints.map((fp) => {
              const state = trustState(fp.username);
              const badge = trustBadge(state);
              const isRotating = rotating === fp.username;

              return (
                <div
                  key={fp.username}
                  className="rounded border border-[var(--border)] bg-[var(--surface)] overflow-hidden"
                >
                  <div className="flex items-center gap-3 px-4 py-3">
                    <div className="w-8 h-8 rounded-full bg-accent/10 flex items-center justify-center flex-shrink-0">
                      <span className="text-[13px] font-bold text-accent capitalize">
                        {fp.username.charAt(0)}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[13px] font-semibold text-[var(--text)] capitalize">
                          {fp.username}
                        </span>
                        <span
                          className={clsx(
                            "px-1.5 py-0.5 text-[9px] font-mono font-medium rounded border",
                            badge.class,
                          )}
                        >
                          {badge.label}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRotate(fp.username)}
                      disabled={!!rotating}
                      className={clsx(
                        "px-3 py-1.5 text-[11px] font-medium rounded border transition-all flex-shrink-0",
                        isRotating
                          ? "bg-quantum-orange/20 text-quantum-orange border-quantum-orange/20 cursor-wait"
                          : "bg-[var(--surface2)] text-[var(--text-dim)] border-[var(--border)] hover:border-quantum-orange hover:text-quantum-orange disabled:opacity-40",
                      )}
                    >
                      {isRotating ? "Rotating..." : "Rotate Keys"}
                    </button>
                  </div>

                  <div className="px-4 pb-3 space-y-1.5">
                    <FingerprintRow label="Kyber768 (KEM)" value={fp.kyber} />
                    <FingerprintRow label="Dilithium3 (SIG)" value={fp.dilithium} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Rotation history */}
      {rotationHistory.length > 0 && (
        <div className="space-y-2">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            Rotation History
          </div>
          <div className="rounded border border-[var(--border)] overflow-hidden">
            {rotationHistory.map((record, i) => (
              <div
                key={i}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2",
                  i < rotationHistory.length - 1 && "border-b border-[var(--border)]",
                  "bg-[var(--surface)]",
                )}
              >
                <span
                  className={clsx(
                    "w-2 h-2 rounded-full flex-shrink-0",
                    record.accepted ? "bg-quantum-green" : "bg-quantum-red",
                  )}
                />
                <div className="flex-1 min-w-0">
                  <span className="text-[11px] font-medium text-[var(--text)] capitalize">
                    {record.username}
                  </span>
                  <span className="text-[10px] text-[var(--text-muted)] ml-2">
                    {record.accepted ? "Key accepted" : "Key rejected (MITM warning)"}
                  </span>
                </div>
                <span className="text-[9px] font-mono text-[var(--text-muted)]">
                  {new Date(record.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Info */}
      <div className="p-3 rounded border border-[var(--border)] bg-[var(--surface)] text-[11px] text-[var(--text-muted)] space-y-1.5">
        <div className="font-medium text-[var(--text-dim)] text-[12px]">
          About Trust-On-First-Use (TOFU)
        </div>
        <p>
          TOFU means the first time you see a user's public key, you trust it. If the fingerprint ever changes,
          a warning is raised because it could mean a man-in-the-middle has substituted their own key.
        </p>
        <p>
          This is the same model used by SSH (<span className="font-mono text-accent">known_hosts</span>) and
          Signal's safety numbers. In production, you'd verify fingerprints out-of-band (QR code, phone call).
        </p>
      </div>
    </div>
  );
}

function FingerprintRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-[10px] font-medium text-[var(--text-muted)] w-28 flex-shrink-0 pt-0.5">
        {label}
      </span>
      <span className="text-[10px] font-mono text-accent break-all leading-relaxed">
        {value || "N/A"}
      </span>
    </div>
  );
}
