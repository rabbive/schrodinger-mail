import { useEffect } from "react";
import clsx from "clsx";

interface Props {
  message: string;
  type: "success" | "error" | "info";
  onDismiss: () => void;
}

export default function Notification({ message, type, onDismiss }: Props) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 3000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div
      className={clsx(
        "fixed top-14 left-1/2 -translate-x-1/2 px-5 py-2 rounded text-xs font-semibold z-50",
        "animate-[fadeIn_0.2s_ease-out] shadow-lg",
        type === "success" && "bg-quantum-green text-white",
        type === "error" && "bg-quantum-red text-white",
        type === "info" && "bg-accent text-white",
      )}
    >
      {message}
    </div>
  );
}
