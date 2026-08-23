import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { AddressSource } from "@/hooks/useContractAddress";
import { explorerAddressUrl } from "@/lib/chains";
import { shortAddress } from "@/lib/format";
import { clsx } from "@/lib/cx";

interface ContractSettingsProps {
  address: `0x${string}`;
  source: AddressSource;
  isCustom: boolean;
  onSave: (value: string) => { ok: true } | { ok: false; error: string };
  onClear: () => void;
}

const SOURCE_META: Record<AddressSource, { label: string; className: string }> = {
  custom: { label: "Custom", className: "border-accent-cyan/40 bg-accent-cyan/10 text-accent-cyan" },
  env: { label: "From env", className: "border-status-accepted/30 bg-status-accepted/10 text-status-accepted" },
  default: { label: "Default", className: "border-status-pending/30 bg-status-pending/10 text-status-pending" },
};

/**
 * Target-contract panel: shows the active address and its source, and lets the
 * user override it inline. Replaces the old "Set VITE_CONTRACT_ADDRESS" blocker.
 */
export function ContractSettings({ address, source, isCustom, onSave, onClear }: ContractSettingsProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(address);
  const [error, setError] = useState<string | null>(null);
  const meta = SOURCE_META[source];

  // keep the draft in sync when the active address changes underneath us
  useEffect(() => {
    if (!editing) setDraft(address);
  }, [address, editing]);

  const commit = () => {
    const res = onSave(draft);
    if (res.ok) {
      setEditing(false);
      setError(null);
    } else {
      setError(res.error);
    }
  };

  const cancel = () => {
    setDraft(address);
    setError(null);
    setEditing(false);
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-widest text-slate-500">Target contract</h3>
        <span className={clsx("rounded-full border px-2 py-0.5 text-[11px] font-semibold", meta.className)}>
          {meta.label}
        </span>
      </div>

      {!editing ? (
        <div className="mt-4 space-y-3">
          <a
            href={explorerAddressUrl(address)}
            target="_blank"
            rel="noreferrer"
            className="block break-all font-mono text-sm text-slate-100 hover:text-accent-cyan"
            title={address}
          >
            {shortAddress(address)} ↗
          </a>
          {source === "default" && (
            <p className="text-xs text-slate-500">
              Using the bundled default deployment. Set VITE_CONTRACT_ADDRESS or enter your own below.
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <button className="btn-ghost !py-2 text-xs" onClick={() => setEditing(true)}>
              {isCustom ? "Change address" : "Use custom address"}
            </button>
            {isCustom && (
              <button className="btn-ghost !py-2 text-xs" onClick={onClear}>
                Reset to default
              </button>
            )}
          </div>
        </div>
      ) : (
        <AnimatePresence>
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 space-y-2"
          >
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value.trim() as `0x${string}`)}
              onKeyDown={(e) => e.key === "Enter" && commit()}
              placeholder="0x…"
              spellCheck={false}
              autoFocus
              className={clsx(
                "field font-mono text-sm",
                error && "border-status-rejected/60 focus:border-status-rejected focus:ring-status-rejected/20",
              )}
            />
            {error && <p className="text-xs text-status-rejected">{error}</p>}
            <div className="flex gap-2">
              <button className="btn-primary !py-2 text-xs" onClick={commit}>
                Save
              </button>
              <button className="btn-ghost !py-2 text-xs" onClick={cancel}>
                Cancel
              </button>
            </div>
          </motion.div>
        </AnimatePresence>
      )}
    </div>
  );
}
