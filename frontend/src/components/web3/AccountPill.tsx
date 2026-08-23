import { useWallet } from "@/hooks/useWallet";
import { explorerAddressUrl } from "@/lib/chains";
import { clsx } from "@/lib/cx";

/** Compact identity chip: gradient avatar + short address + live balance. */
export function AccountPill({ className }: { className?: string }) {
  const { address, displayAddress, formattedBalance, balanceSymbol, balanceLoading } = useWallet();
  if (!address) return null;

  return (
    <div className={clsx("flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-1.5", className)}>
      <span
        className="h-7 w-7 rounded-lg"
        style={{
          background: `conic-gradient(from 120deg, #38e1ff, #9b6bff, #ff5cf4, #38e1ff)`,
        }}
        aria-hidden
      />
      <div className="leading-tight">
        <a
          href={explorerAddressUrl(address)}
          target="_blank"
          rel="noreferrer"
          className="block font-mono text-sm text-slate-100 hover:text-accent-cyan"
        >
          {displayAddress}
        </a>
        <span className="text-xs text-slate-400">
          {balanceLoading ? "…" : `${formattedBalance} ${balanceSymbol}`}
        </span>
      </div>
    </div>
  );
}
