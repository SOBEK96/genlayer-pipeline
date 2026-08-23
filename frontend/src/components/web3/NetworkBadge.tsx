import { useNetwork } from "@/hooks/useNetwork";
import { useToast } from "@/context/ToastContext";
import { clsx } from "@/lib/cx";

/** Live network status + one-click switch to the target GenLayer chain. */
export function NetworkBadge({ className }: { className?: string }) {
  const { isConnected, isCorrectNetwork, activeChainName, targetChain, isSwitching, switchToTarget } =
    useNetwork();
  const toast = useToast();

  if (!isConnected) return null;

  const handleSwitch = async () => {
    const res = await switchToTarget();
    if (!res.ok) {
      toast.push({ variant: "error", title: res.error.title, message: res.error.detail });
    } else {
      toast.push({ variant: "success", title: "Network switched", message: `Now on ${targetChain.name}.` });
    }
  };

  if (isCorrectNetwork) {
    return (
      <span
        className={clsx(
          "inline-flex items-center gap-2 rounded-xl border border-status-accepted/30 bg-status-accepted/10 px-3 py-1.5 text-sm text-status-accepted",
          className,
        )}
      >
        <span className="h-2 w-2 rounded-full bg-status-accepted shadow-[0_0_10px_rgba(55,245,163,0.8)]" />
        {activeChainName}
      </span>
    );
  }

  return (
    <button
      onClick={handleSwitch}
      disabled={isSwitching}
      className={clsx(
        "inline-flex items-center gap-2 rounded-xl border border-status-pending/40 bg-status-pending/10 px-3 py-1.5 text-sm font-medium text-status-pending transition hover:bg-status-pending/20 disabled:opacity-60",
        className,
      )}
    >
      <span className="h-2 w-2 rounded-full bg-status-pending animate-glow-pulse" />
      {isSwitching ? "Switching…" : `Switch to ${targetChain.name}`}
    </button>
  );
}
