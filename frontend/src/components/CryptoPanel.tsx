import { useStore } from "@/hooks/useStore";
import clsx from "clsx";
import type { CryptoStep } from "@/types";

export default function CryptoPanel() {
  const { cryptoLog, clearCryptoLog } = useStore();

  return (
    <aside className="border-l border-[var(--border)] bg-[var(--surface)] flex flex-col max-lg:hidden">
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-[var(--border)]">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
          Crypto Log
        </span>
        {cryptoLog.length > 0 && (
          <button
            onClick={clearCryptoLog}
            className="text-[10px] text-[var(--text-muted)] hover:text-[var(--text)] transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin p-2 space-y-1.5">
        {cryptoLog.length === 0 ? (
          <div className="text-center text-[11px] text-[var(--text-muted)] py-10 leading-relaxed px-4">
            Send or receive an email to see the
            <br />
            cryptographic process here.
          </div>
        ) : (
          cryptoLog.map((step, i) => <StepCard key={i} step={step} />)
        )}
      </div>
    </aside>
  );
}

function StepCard({ step }: { step: CryptoStep }) {
  const statusConfig = {
    success: { dot: "bg-quantum-green", text: "text-quantum-green", bg: "bg-quantum-green/8" },
    error: { dot: "bg-quantum-red", text: "text-quantum-red", bg: "bg-quantum-red/8" },
    info: { dot: "bg-quantum-blue", text: "text-quantum-blue", bg: "bg-quantum-blue/8" },
  };
  const cfg = statusConfig[step.status];

  return (
    <div className="rounded border border-[var(--border)] bg-[var(--bg)] overflow-hidden animate-fade-slide">
      <div className="flex items-start gap-2 p-2">
        <span
          className={clsx(
            "w-[18px] h-[18px] rounded flex items-center justify-center text-[9px] font-bold flex-shrink-0 mt-px",
            cfg.bg,
            cfg.text,
          )}
        >
          {step.step}
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-semibold leading-snug text-[var(--text)]">{step.title}</div>
          <div className="text-[10px] text-[var(--text-dim)] mt-0.5 leading-snug">
            {step.description}
          </div>
        </div>
      </div>
      {step.details && Object.keys(step.details).length > 0 && (
        <div className="px-2 pb-2 pt-0">
          <div className="rounded bg-[var(--surface)] p-1.5">
            <table className="w-full text-[9px] font-mono">
              <tbody>
                {Object.entries(step.details).map(([k, v]) => (
                  <tr key={k}>
                    <td className="text-[var(--text-muted)] pr-2 whitespace-nowrap align-top py-[1px]">
                      {k}
                    </td>
                    <td className="text-accent break-all align-top py-[1px]">
                      {String(v)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
