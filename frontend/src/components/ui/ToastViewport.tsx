import { AnimatePresence, motion } from "framer-motion";
import { useToast, type ToastVariant } from "@/context/ToastContext";
import { Spinner } from "./Spinner";
import { explorerTxUrl } from "@/lib/chains";
import { shortHash } from "@/lib/format";
import { clsx } from "@/lib/cx";

const ACCENT: Record<ToastVariant, string> = {
  success: "from-status-accepted/60 to-accent-cyan/40",
  error: "from-status-rejected/60 to-accent-magenta/40",
  info: "from-accent-cyan/50 to-accent-violet/40",
  pending: "from-status-pending/50 to-accent-violet/40",
};

const ICON: Record<ToastVariant, string> = {
  success: "✓",
  error: "✕",
  info: "ⓘ",
  pending: "",
};

/** Fixed, stacked glassmorphic toast surface. Mount once, near the app root. */
export function ToastViewport() {
  const { toasts, dismiss } = useToast();

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-[min(92vw,22rem)] flex-col gap-3">
      <AnimatePresence initial={false}>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            layout
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: 40, scale: 0.96 }}
            transition={{ type: "spring", stiffness: 320, damping: 26 }}
            className="pointer-events-auto"
          >
            <div className="glass relative overflow-hidden p-4">
              <div className={clsx("absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r", ACCENT[t.variant])} />
              <div className="flex items-start gap-3">
                <div className="mt-0.5 shrink-0">
                  {t.variant === "pending" ? (
                    <Spinner size={20} />
                  ) : (
                    <span
                      className={clsx(
                        "flex h-6 w-6 items-center justify-center rounded-full bg-gradient-to-br text-xs font-bold text-base-900",
                        ACCENT[t.variant],
                      )}
                    >
                      {ICON[t.variant]}
                    </span>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-slate-100">{t.title}</p>
                  {t.message && <p className="mt-0.5 break-words text-xs text-slate-400">{t.message}</p>}
                  {t.hash && (
                    <div className="mt-2 flex items-center gap-2">
                      <a
                        href={explorerTxUrl(t.hash)}
                        target="_blank"
                        rel="noreferrer"
                        className="font-mono text-xs text-accent-cyan hover:underline"
                      >
                        {shortHash(t.hash)} ↗
                      </a>
                      <button
                        onClick={() => navigator.clipboard?.writeText(t.hash!)}
                        className="text-xs text-slate-500 hover:text-slate-300"
                        aria-label="Copy transaction hash"
                      >
                        copy
                      </button>
                    </div>
                  )}
                </div>
                <button
                  onClick={() => dismiss(t.id)}
                  className="shrink-0 rounded-md px-1 text-slate-500 hover:text-slate-200"
                  aria-label="Dismiss notification"
                >
                  ✕
                </button>
              </div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
