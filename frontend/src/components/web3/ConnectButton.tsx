import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { Connector } from "wagmi";
import { useWallet } from "@/hooks/useWallet";
import { useToast } from "@/context/ToastContext";
import { AccountPill } from "./AccountPill";
import { translateError } from "@/lib/errors";
import { clsx } from "@/lib/cx";

const ICONS: Record<string, string> = {
  metaMask: "🦊",
  metaMaskSDK: "🦊",
  walletConnect: "🔗",
  injected: "🧩",
};

const LABELS: Record<string, string> = {
  metaMask: "MetaMask",
  metaMaskSDK: "MetaMask",
  walletConnect: "WalletConnect",
  injected: "Browser Wallet",
};

/** Wallet connect entry point: pill when connected, glass picker modal otherwise. */
export function ConnectButton() {
  const { isConnected, isConnecting, connectors, connect, disconnect } = useWallet();
  const toast = useToast();
  const [open, setOpen] = useState(false);

  // De-duplicate connectors by display label (wagmi can list overlaps)
  const options = useMemo(() => {
    const seen = new Set<string>();
    return connectors.filter((c) => {
      const label = LABELS[c.id] ?? c.name;
      if (seen.has(label)) return false;
      seen.add(label);
      return true;
    });
  }, [connectors]);

  const handleConnect = async (c: Connector) => {
    try {
      await connect(c);
      setOpen(false);
      toast.push({ variant: "success", title: "Wallet connected", message: LABELS[c.id] ?? c.name });
    } catch (err) {
      const f = translateError(err);
      toast.push({ variant: f.cancelled ? "info" : "error", title: f.title, message: f.detail });
    }
  };

  if (isConnected) {
    return (
      <div className="flex items-center gap-2">
        <AccountPill />
        <button onClick={() => disconnect()} className="btn-ghost !py-2 text-xs">
          Disconnect
        </button>
      </div>
    );
  }

  return (
    <>
      <button className="btn-primary" onClick={() => setOpen(true)} disabled={isConnecting}>
        {isConnecting ? "Connecting…" : "Connect Wallet"}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="absolute inset-0 bg-base-900/70 backdrop-blur-sm" onClick={() => setOpen(false)} />
            <motion.div
              initial={{ scale: 0.92, y: 20, opacity: 0 }}
              animate={{ scale: 1, y: 0, opacity: 1 }}
              exit={{ scale: 0.92, y: 20, opacity: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 26 }}
              className="glass relative z-10 w-full max-w-sm p-6"
            >
              <h3 className="text-lg font-bold text-gradient">Connect a wallet</h3>
              <p className="mt-1 text-sm text-slate-400">Choose a provider to enter the console.</p>
              <div className="mt-5 space-y-2">
                {options.length === 0 && (
                  <p className="rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm text-slate-400">
                    No wallet detected. Install MetaMask or configure a WalletConnect projectId.
                  </p>
                )}
                {options.map((c) => (
                  <button
                    key={c.uid}
                    onClick={() => handleConnect(c)}
                    className={clsx(
                      "flex w-full items-center gap-3 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-left",
                      "transition hover:border-accent-cyan/40 hover:bg-white/[0.08]",
                    )}
                  >
                    <span className="text-xl">{ICONS[c.id] ?? "👛"}</span>
                    <span className="font-medium text-slate-100">{LABELS[c.id] ?? c.name}</span>
                  </button>
                ))}
              </div>
              <button onClick={() => setOpen(false)} className="btn-ghost mt-5 w-full">
                Cancel
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
