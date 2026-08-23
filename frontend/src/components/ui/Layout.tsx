import { useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ConnectButton } from "@/components/web3/ConnectButton";
import { NetworkBadge } from "@/components/web3/NetworkBadge";
import { clsx } from "@/lib/cx";

const NAV = [
  { to: "/", label: "Home", end: true },
  { to: "/dashboard", label: "Dashboard", end: false },
  { to: "/action", label: "Action Hub", end: false },
  { to: "/history", label: "History", end: false },
];

function NavItem({ to, label, end }: { to: string; label: string; end: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        clsx(
          "relative rounded-xl px-4 py-2 text-sm font-medium transition-colors",
          isActive ? "text-slate-50" : "text-slate-400 hover:text-slate-200",
        )
      }
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <motion.span
              layoutId="nav-active"
              className="absolute inset-0 rounded-xl border border-white/10 bg-white/[0.06] shadow-glow"
              transition={{ type: "spring", stiffness: 380, damping: 30 }}
            />
          )}
          <span className="relative">{label}</span>
        </>
      )}
    </NavLink>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-white/5 bg-base-900/50 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-accent-cyan to-accent-violet font-mono text-sm font-black text-base-900 shadow-glow">
              P
            </div>
            <div className="leading-tight">
              <p className="text-sm font-extrabold tracking-tight text-slate-50">PipeLine</p>
              <p className="-mt-0.5 text-[11px] text-slate-400">GenLayer CI/CD Console</p>
            </div>
          </div>

          <nav className="hidden items-center gap-1 md:flex">
            {NAV.map((n) => (
              <NavItem key={n.to} {...n} />
            ))}
          </nav>

          <div className="hidden items-center gap-3 md:flex">
            <NetworkBadge />
            <ConnectButton />
          </div>

          <button
            className="btn-ghost md:hidden"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label="Toggle menu"
          >
            ☰
          </button>
        </div>

        <AnimatePresence>
          {menuOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden border-t border-white/5 md:hidden"
            >
              <div className="space-y-3 px-4 py-4">
                <div className="flex flex-col gap-1" onClick={() => setMenuOpen(false)}>
                  {NAV.map((n) => (
                    <NavItem key={n.to} {...n} />
                  ))}
                </div>
                <div className="flex flex-wrap items-center gap-3 pt-2">
                  <NetworkBadge />
                  <ConnectButton />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">{children}</main>

      <footer className="mx-auto max-w-7xl px-4 pb-10 pt-4 text-center text-xs text-slate-600 sm:px-6">
        PipeLine · target-agnostic CI/CD for GenLayer intelligent contracts
      </footer>
    </div>
  );
}
