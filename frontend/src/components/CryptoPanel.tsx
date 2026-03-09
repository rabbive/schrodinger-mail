import { useStore } from "@/hooks/useStore";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { CryptoStep } from "@/types";
import { Eraser, Lock, Activity } from "lucide-react";

export default function CryptoPanel() {
  const { cryptoLog, clearCryptoLog } = useStore();

  return (
    <aside className="border-l bg-card flex flex-col max-lg:hidden">
      <div className="flex items-center justify-between px-3 py-2.5 border-b">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <Activity className="w-3 h-3" />
          Crypto Log
        </span>
        {cryptoLog.length > 0 && (
          <Button variant="ghost" size="sm" onClick={clearCryptoLog} className="h-5 px-1.5 text-[10px]">
            <Eraser className="w-3 h-3" />
            Clear
          </Button>
        )}
      </div>

      <ScrollArea className="flex-1 p-2">
        <div className="space-y-1.5">
          {cryptoLog.length === 0 ? (
            <div className="text-center text-[11px] text-muted-foreground py-10 leading-relaxed px-4">
              <Lock className="w-6 h-6 mx-auto mb-2 opacity-30" />
              Send or receive an email to see the
              <br />
              cryptographic process here.
            </div>
          ) : (
            cryptoLog.map((step, i) => <StepCard key={i} step={step} />)
          )}
        </div>
      </ScrollArea>
    </aside>
  );
}

function StepCard({ step }: { step: CryptoStep }) {
  const statusConfig = {
    success: { text: "text-quantum-green", bg: "bg-quantum-green/8" },
    error: { text: "text-destructive", bg: "bg-destructive/8" },
    info: { text: "text-quantum-blue", bg: "bg-quantum-blue/8" },
  };
  const cfg = statusConfig[step.status];

  return (
    <div className="rounded-md border bg-background overflow-hidden animate-fade-slide">
      <div className="flex items-start gap-2 p-2">
        <span
          className={cn(
            "w-[18px] h-[18px] rounded-md flex items-center justify-center text-[9px] font-bold flex-shrink-0 mt-px",
            cfg.bg,
            cfg.text,
          )}
        >
          {step.step}
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-semibold leading-snug text-foreground">{step.title}</div>
          <div className="text-[10px] text-muted-foreground mt-0.5 leading-snug">
            {step.description}
          </div>
        </div>
      </div>
      {step.details && Object.keys(step.details).length > 0 && (
        <div className="px-2 pb-2 pt-0">
          <div className="rounded-md bg-card p-1.5">
            <table className="w-full text-[9px] font-mono">
              <tbody>
                {Object.entries(step.details).map(([k, v]) => (
                  <tr key={k}>
                    <td className="text-muted-foreground pr-2 whitespace-nowrap align-top py-[1px]">
                      {k}
                    </td>
                    <td className="text-primary break-all align-top py-[1px]">
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
