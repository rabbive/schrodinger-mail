import { useStore } from "@/hooks/useStore";
import clsx from "clsx";
import type { CryptoStep } from "@/types";

export default function CryptoPanel() {
  const { cryptoLog, clearCryptoLog } = useStore();

  return (
    <aside className="border-l border-[var(--border)] bg-[var(--surface)] flex flex-col max-lg:hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border)]">
        <span className="text-[10px] font-bold uppercase tracking-wider text-accent-light">
          Crypto Process Log
        </span>
        <button
          onClick={clearCryptoLog}
          className="text-[10px] text-[var(--text-dim)] hover:text-[var(--text)] transition-colors"
        >
          Clear
        </button>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin p-2 space-y-1.5">
        {cryptoLog.length === 0 ? (
          <div className="text-center text-xs text-[var(--text-dim)] py-8 leading-relaxed">
            Send or receive an email to see the
            <br />
            step-by-step cryptographic process here.
          </div>
        ) : (
          cryptoLog.map((step, i) => <StepCard key={i} step={step} />)
        )}
      </div>
    </aside>
  );
}

function StepCard({ step }: { step: CryptoStep }) {
  const statusColors = {
    success: "bg-quantum-green/15 text-quantum-green",
    error: "bg-quantum-red/15 text-quantum-red",
    info: "bg-quantum-blue/15 text-quantum-blue",
  };

  return (
    <div className="rounded border border-[var(--border)] bg-[var(--bg)] overflow-hidden animate-[fadeSlideIn_0.3s_ease-out]">
      <div className="flex items-start gap-1.5 p-2">
        <span
          className={clsx(
            "w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold flex-shrink-0",
            statusColors[step.status],
          )}
        >
          {step.step}
        </span>
        <div className="min-w-0">
          <div className="text-[11px] font-semibold leading-snug">{step.title}</div>
          <div className="text-[10px] text-[var(--text-dim)] mt-0.5 leading-snug">
            {step.description}
          </div>
        </div>
      </div>
      {step.details && Object.keys(step.details).length > 0 && (
        <div className="px-2 pb-2">
          <table className="w-full text-[9px] font-mono">
            <tbody>
              {Object.entries(step.details).map(([k, v]) => (
                <tr key={k}>
                  <td className="text-[var(--text-dim)] pr-2 whitespace-nowrap align-top py-0.5">
                    {k}
                  </td>
                  <td className="text-quantum-blue break-all align-top py-0.5">
                    {String(v)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
