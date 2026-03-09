import { useEffect } from "react";
import clsx from "clsx";

interface Props {
  message: string;
  type: "success" | "error" | "info";
  onDismiss: () => void;
}

export default function Notification({ message, type, onDismiss }: Props) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 3500);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div
      className={clsx(
        "fixed top-14 left-1/2 -translate-x-1/2 px-4 py-2 rounded text-[12px] font-medium z-50",
        "animate-fade-in shadow-lg border",
        type === "success" && "bg-quantum-green/15 text-quantum-green border-quantum-green/30",
        type === "error" && "bg-quantum-red/15 text-quantum-red border-quantum-red/30",
        type === "info" && "bg-accent/15 text-accent border-accent/30",
      )}
    >
      {message}
    </div>
  );
}
