import { useEffect } from "react";
import { X } from "lucide-react";
import { cn } from "../lib/utils";

interface ToastProps {
  message: string;
  type: "success" | "error";
  onClose: () => void;
  visible: boolean;
}

export function Toast({ message, type, onClose, visible }: ToastProps) {
  useEffect(() => {
    if (!visible) return;
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  }, [visible, onClose]);

  if (!visible) return null;

  return (
    <div
      className={cn(
        "toast",
        type === "success" && "toast-success",
        type === "error" && "toast-error",
        visible && "toast-show"
      )}
      role="alert"
      aria-live="polite"
    >
      <span className="text-sm">{message}</span>
      <button
        onClick={onClose}
        className="ml-2 p-1 rounded hover:bg-white/10 transition-colors"
        aria-label="Dismiss"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}