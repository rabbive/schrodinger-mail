import { useStore } from "@/hooks/useStore";

export default function EmailReader() {
  const { emails, selectedEmailId } = useStore();

  const selected = emails.find((e) => e.id === selectedEmailId);

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
    <div className="max-w-2xl">
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-base font-semibold text-[var(--text)]">{selected.subject || "(no subject)"}</span>
          {selected.verified ? (
            <span className="px-1.5 py-0.5 bg-quantum-green/10 text-quantum-green text-[10px] font-mono font-medium rounded">
              verified
            </span>
          ) : (
            <span className="px-1.5 py-0.5 bg-quantum-red/10 text-quantum-red text-[10px] font-mono font-medium rounded">
              unverified
            </span>
          )}
        </div>
        <div className="text-[12px] text-[var(--text-dim)] space-y-0.5">
          <div>
            From: <span className="font-medium capitalize text-[var(--text)]">{selected.sender}</span>
          </div>
          {selected.thread_id && (
            <div>
              Thread: <span className="font-mono text-accent text-[11px]">{selected.thread_id.slice(0, 8)}...</span>
            </div>
          )}
          <div className="text-[var(--text-muted)]">{selected.timestamp}</div>
        </div>
      </div>

      {selected.error && (
        <div className="mb-3 p-3 bg-quantum-red/8 border border-quantum-red/20 rounded text-[12px] text-quantum-red">
          {selected.error}
        </div>
      )}

      <div className="p-4 bg-[var(--surface)] border border-[var(--border)] rounded text-[13px] whitespace-pre-wrap leading-relaxed font-mono text-[var(--text)]">
        {bodyText}
      </div>

      <div className="flex gap-2 mt-4">
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
