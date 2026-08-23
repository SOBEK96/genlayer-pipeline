import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { TiltCard } from "@/components/3d/TiltCard";
import { ConnectButton } from "@/components/web3/ConnectButton";
import { Spinner } from "@/components/ui/Spinner";
import { useWallet } from "@/hooks/useWallet";
import { useNetwork } from "@/hooks/useNetwork";
import { useActivity } from "@/hooks/useActivity";

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};
const item = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 260, damping: 24 } },
};

export function Dashboard() {
  const { isConnected, formattedBalance, balanceSymbol, balanceLoading, displayAddress } = useWallet();
  const { isCorrectNetwork, activeChainName, targetChain } = useNetwork();
  const { items, loading } = useActivity();

  if (!isConnected) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <TiltCard className="w-full max-w-lg" max={8}>
          <div className="space-y-4 text-center animate-float">
            <h1 className="text-3xl font-extrabold text-gradient">Enter the PipeLine Console</h1>
            <p className="text-slate-400">
              Connect an EVM wallet to view live account stats, submit intelligent-contract
              actions, and track validator consensus in real time.
            </p>
            <div className="flex justify-center pt-2">
              <ConnectButton />
            </div>
          </div>
        </TiltCard>
      </div>
    );
  }

  const accepted = items.filter((a) => a.status === "ACCEPTED").length;
  const pending = items.filter((a) => a.status === "PENDING").length;

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-8">
      <motion.div variants={item} className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-50">Spatial Dashboard</h1>
          <p className="mt-1 text-slate-400">
            Welcome back, <span className="font-mono text-slate-300">{displayAddress}</span>
          </p>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        <motion.div variants={item}>
          <TiltCard>
            <p className="text-xs uppercase tracking-widest text-slate-500">Native Balance</p>
            <div className="mt-3 flex items-baseline gap-2">
              {balanceLoading ? (
                <Spinner size={22} />
              ) : (
                <span className="text-4xl font-extrabold text-slate-50">{formattedBalance}</span>
              )}
              <span className="text-lg font-semibold text-accent-cyan">{balanceSymbol}</span>
            </div>
            <p className="mt-2 text-xs text-slate-500">Updated live every 15s</p>
          </TiltCard>
        </motion.div>

        <motion.div variants={item}>
          <TiltCard>
            <p className="text-xs uppercase tracking-widest text-slate-500">Network Status</p>
            <div className="mt-3 flex items-center gap-3">
              <span
                className={`h-3 w-3 rounded-full ${
                  isCorrectNetwork ? "bg-status-accepted shadow-[0_0_12px_rgba(55,245,163,0.9)]" : "bg-status-pending animate-glow-pulse"
                }`}
              />
              <span className="text-2xl font-bold text-slate-50">
                {isCorrectNetwork ? activeChainName : "Wrong network"}
              </span>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              {isCorrectNetwork ? "Connected to target chain" : `Expected ${targetChain.name}`}
            </p>
          </TiltCard>
        </motion.div>

        <motion.div variants={item}>
          <TiltCard>
            <p className="text-xs uppercase tracking-widest text-slate-500">Consensus Activity</p>
            <div className="mt-3 flex items-end gap-4">
              <div>
                <p className="text-4xl font-extrabold text-status-accepted">{loading ? "—" : accepted}</p>
                <p className="text-xs text-slate-500">accepted</p>
              </div>
              <div>
                <p className="text-4xl font-extrabold text-status-pending">{loading ? "—" : pending}</p>
                <p className="text-xs text-slate-500">pending</p>
              </div>
            </div>
          </TiltCard>
        </motion.div>
      </div>

      {/* Quick-action portals */}
      <motion.div variants={item} className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <Portal to="/action" title="Submit an Action" desc="Open the interactive submission hub with live gas estimation." accent="from-accent-cyan/20 to-transparent" />
        <Portal to="/history" title="Activity Stream" desc="Browse past transactions and validator consensus states." accent="from-accent-violet/20 to-transparent" />
      </motion.div>
    </motion.div>
  );
}

function Portal({ to, title, desc, accent }: { to: string; title: string; desc: string; accent: string }) {
  return (
    <Link to={to} className="group block">
      <TiltCard max={6}>
        <div className={`pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-br ${accent}`} />
        <div className="relative flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold text-slate-50">{title}</h3>
            <p className="mt-1 max-w-xs text-sm text-slate-400">{desc}</p>
          </div>
          <span className="text-2xl text-accent-cyan transition-transform group-hover:translate-x-1">→</span>
        </div>
      </TiltCard>
    </Link>
  );
}
