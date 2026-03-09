import { useEffect, useState } from "react";
import { useStore } from "@/hooks/useStore";
import { api } from "@/services/api";
import clsx from "clsx";

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
      <div className="flex flex-col items-center justify-center h-64 text-[var(--text-muted)]">
        <div className="w-10 h-10 rounded-lg bg-[var(--surface2)] border border-[var(--border)] flex items-center justify-center text-lg mb-3">
          ✉
        </div>
        <div className="text-[12px]">Select an email from the sidebar to read it.</div>
      </div>
    );
  }

  const bodyText = selected.plaintext
    ? extractBody(selected.plaintext)
    : "(Unable to decrypt)";

  return (
    <div className="max-w-2xl space-y-4">
      {/* Email header */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-base font-semibold text-[var(--text)]">
            {selected.subject || "(no subject)"}
          </span>
          {selected.verified ? (
            <span className="px-1.5 py-0.5 bg-quantum-green/10 text-quantum-green text-[10px] font-mono font-medium rounded">
              verified
            </span>
          ) : (
            <span className="px-1.5 py-0.5 bg-quantum-red/10 text-quantum-red text-[10px] font-mono font-medium rounded">
              {selected.error?.toLowerCase().includes("tamper")
                ? "tampered"
                : selected.error?.toLowerCase().includes("signature")
                  ? "forged"
                  : selected.error?.toLowerCase().includes("replay")
                    ? "replay"
                    : "unverified"}
            </span>
          )}
        </div>
        <div className="text-[12px] text-[var(--text-dim)] space-y-0.5">
          <div>
            From:{" "}
            <span className="font-medium capitalize text-[var(--text)]">
              {selected.sender}
            </span>
          </div>
          {selected.thread_id && (
            <div>
              Thread:{" "}
              <span className="font-mono text-accent text-[11px]">
                {selected.thread_id.slice(0, 8)}...
              </span>
            </div>
          )}
          <div className="text-[var(--text-muted)]">{selected.timestamp}</div>
        </div>
      </div>

      {/* Error */}
      {selected.error && (
        <div className="p-3 bg-quantum-red/8 border border-quantum-red/20 rounded text-[12px] text-quantum-red">
          {selected.error}
        </div>
      )}

      {/* Email body */}
      <div className="p-4 bg-[var(--surface)] border border-[var(--border)] rounded text-[13px] whitespace-pre-wrap leading-relaxed font-mono text-[var(--text)]">
        {bodyText}
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button className="px-3 py-1.5 bg-accent text-white text-[12px] font-medium rounded hover:bg-accent-light transition-colors">
          Reply
        </button>
        <button className="px-3 py-1.5 bg-[var(--surface2)] text-[var(--text-dim)] text-[12px] font-medium rounded border border-[var(--border)] hover:bg-[var(--surface3)] transition-colors">
          Forward
        </button>
        <button className="px-3 py-1.5 bg-[var(--surface2)] text-[var(--text-dim)] text-[12px] font-medium rounded border border-[var(--border)] hover:bg-[var(--surface3)] transition-colors">
          Archive
        </button>
        <button className="px-3 py-1.5 bg-quantum-red/10 text-quantum-red text-[12px] font-medium rounded border border-quantum-red/20 hover:bg-quantum-red/15 transition-colors">
          Delete
        </button>
      </div>

      {/* Verification Panel */}
      <div className="border border-[var(--border)] rounded overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2 bg-[var(--surface)] border-b border-[var(--border)]">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            Verification Evidence
          </span>
          {details && (
            <button
              onClick={() => setShowJson(!showJson)}
              className="text-[10px] text-accent hover:text-accent-light transition-colors"
            >
              {showJson ? "Hide JSON" : "Show JSON"}
            </button>
          )}
        </div>

        {loadingDetails ? (
          <div className="flex items-center justify-center py-6">
            <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        ) : details ? (
          <div className="p-3 space-y-3 bg-[var(--bg)]">
            {/* Checks */}
            <div className="space-y-1">
              {details.checks.map((check, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 px-2.5 py-1.5 rounded bg-[var(--surface)] border border-[var(--border)]"
                >
                  <span
                    className={clsx(
                      "w-4 h-4 rounded flex items-center justify-center text-[8px] font-bold flex-shrink-0 mt-0.5",
                      check.status === "pass"
                        ? "bg-quantum-green/15 text-quantum-green"
                        : "bg-quantum-red/15 text-quantum-red",
                    )}
                  >
                    {check.status === "pass" ? "✓" : "✗"}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-[11px] font-medium text-[var(--text)]">
                      {check.check}
                    </div>
                    <div className="text-[10px] text-[var(--text-dim)] mt-0.5 leading-snug">
                      {check.detail}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Metadata grid */}
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

            {/* JSON view */}
            {showJson && (
              <div className="mt-2">
                <pre className="p-3 bg-[var(--surface)] border border-[var(--border)] rounded text-[10px] font-mono text-[var(--text-dim)] overflow-x-auto max-h-60 scrollbar-thin">
                  {JSON.stringify(details, null, 2)}
                </pre>
              </div>
            )}
          </div>
        ) : (
          <div className="p-4 text-center text-[11px] text-[var(--text-muted)]">
            Verification data unavailable.
          </div>
        )}
      </div>
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
    <div className="px-2.5 py-1.5 rounded bg-[var(--surface)] border border-[var(--border)]">
      <div className="text-[9px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
        {label}
      </div>
      <div
        className={clsx(
          "text-[11px] text-accent mt-0.5 break-all leading-snug",
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
