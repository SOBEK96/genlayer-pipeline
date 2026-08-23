import { useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { clsx } from "@/lib/cx";

export interface AccordionItemData {
  id: string;
  question: string;
  answer: ReactNode;
}

/**
 * Accessible, animated accordion. One panel open at a time; the open panel
 * springs down with a smooth height transition. Purely presentational styling
 * comes from the shared glass tokens.
 */
export function Accordion({ items }: { items: AccordionItemData[] }) {
  const [openId, setOpenId] = useState<string | null>(items[0]?.id ?? null);

  return (
    <div className="space-y-3">
      {items.map((it) => {
        const isOpen = openId === it.id;
        return (
          <div
            key={it.id}
            className={clsx(
              "overflow-hidden rounded-2xl border transition-colors",
              isOpen
                ? "border-accent-cyan/30 bg-white/[0.05]"
                : "border-white/10 bg-white/[0.02] hover:border-white/20",
            )}
          >
            <button
              type="button"
              onClick={() => setOpenId(isOpen ? null : it.id)}
              aria-expanded={isOpen}
              className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
            >
              <span
                className={clsx(
                  "text-base font-semibold transition-colors",
                  isOpen ? "text-slate-50" : "text-slate-200",
                )}
              >
                {it.question}
              </span>
              <motion.span
                animate={{ rotate: isOpen ? 45 : 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 22 }}
                className={clsx(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-lg leading-none",
                  isOpen
                    ? "border-accent-cyan/50 bg-accent-cyan/15 text-accent-cyan"
                    : "border-white/15 text-slate-400",
                )}
                aria-hidden
              >
                +
              </motion.span>
            </button>

            <AnimatePresence initial={false}>
              {isOpen && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.25, ease: "easeInOut" }}
                  className="overflow-hidden"
                >
                  <div className="px-5 pb-5 text-sm leading-relaxed text-slate-400">{it.answer}</div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}
