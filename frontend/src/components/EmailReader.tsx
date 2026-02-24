import { useState } from "react";
import { useStore } from "@/hooks/useStore";
import clsx from "clsx";

export default function EmailReader() {
  const { emails } = useStore();
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const selected = emails.find((e) => e.id === selectedId);

  if (!selected) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-[var(--text-dim)]">
        <div className="text-4xl mb-3">✉</div>
        <div className="text-sm">Select an email from the sidebar to read it.</div>
      </div>
    );
  }

  const bodyText = selected.plaintext
    ? extractBody(selected.plaintext)
    : "(Unable to decrypt)";

  return (
    <div className="max-w-2xl">
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-lg font-bold">{selected.subject || "(no subject)"}</span>
          {selected.verified ? (
            <span className="px-2 py-0.5 bg-quantum-green/15 text-quantum-green text-[10px] font-bold rounded">
              ✓ Verified
            </span>
          ) : (
            <span className="px-2 py-0.5 bg-quantum-red/15 text-quantum-red text-[10px] font-bold rounded">
              ✗ Verification Failed
            </span>
          )}
        </div>
        <div className="text-xs text-[var(--text-dim)] space-y-0.5">
          <div>
            From: <span className="font-semibold capitalize text-[var(--text)]">{selected.sender}</span>
          </div>
          {selected.thread_id && (
            <div>
              Thread: <span className="font-mono text-quantum-blue">{selected.thread_id.slice(0, 8)}...</span>
            </div>
          )}
          <div>{selected.timestamp}</div>
        </div>
      </div>

      {selected.error && (
        <div className="mb-3 p-3 bg-quantum-red/10 border border-quantum-red/30 rounded text-xs text-quantum-red">
          {selected.error}
        </div>
      )}

      <div className="p-4 bg-[var(--surface)] border border-[var(--border)] rounded text-sm whitespace-pre-wrap leading-relaxed font-mono">
        {bodyText}
      </div>

      <div className="flex gap-2 mt-4">
        <button className="px-3 py-1.5 bg-accent text-white text-xs font-semibold rounded hover:bg-accent-light transition-colors">
          Reply
        </button>
        <button className="px-3 py-1.5 bg-[var(--surface2)] text-[var(--text-dim)] text-xs font-medium rounded hover:bg-[var(--border)] transition-colors">
          Forward
        </button>
        <button className="px-3 py-1.5 bg-[var(--surface2)] text-[var(--text-dim)] text-xs font-medium rounded hover:bg-[var(--border)] transition-colors">
          Archive
        </button>
        <button className="px-3 py-1.5 bg-quantum-red/15 text-quantum-red text-xs font-medium rounded hover:bg-quantum-red/25 transition-colors">
          Delete
        </button>
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
