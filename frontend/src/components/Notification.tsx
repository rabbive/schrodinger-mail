import { useEffect } from "react";
import { cn } from "@/lib/utils";
import { CheckCircle2, XCircle, Info } from "lucide-react";

interface Props {
  message: string;
  type: "success" | "error" | "info";
  onDismiss: () => void;
}

const ICON_MAP = {
  success: CheckCircle2,
  error: XCircle,
  info: Info,
};

export default function Notification({ message, type, onDismiss }: Props) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 3500);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  const Icon = ICON_MAP[type];

  return (
    <div
      className={cn(
        "fixed top-14 left-1/2 -translate-x-1/2 px-4 py-2 rounded-md text-[12px] font-medium z-50",
        "animate-fade-in shadow-lg border flex items-center gap-2",
        type === "success" && "bg-quantum-green/15 text-quantum-green border-quantum-green/30",
        type === "error" && "bg-destructive/15 text-destructive border-destructive/30",
        type === "info" && "bg-primary/15 text-primary border-primary/30",
      )}
    >
      <Icon className="w-3.5 h-3.5 flex-shrink-0" />
      {message}
    </div>
  );
}
