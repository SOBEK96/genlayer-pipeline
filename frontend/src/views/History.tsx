import { motion, AnimatePresence } from "framer-motion";
import { GlassCard } from "@/components/3d/GlassCard";
import { SkeletonRow } from "@/components/3d/Skeleton";
import { StatusBadge, type ConsensusStatus } from "@/components/ui/StatusBadge";
import { useActivity, useActivityFilter } from "@/hooks/useActivity";
import { explorerTxUrl } from "@/lib/chains";
import { shortHash, relativeTime } from "@/lib/format";
import { clsx } from "@/lib/cx";

const FILTERS: Array<ConsensusStatus | "ALL"> = ["ALL", "ACCEPTED", "PENDING", "REJECTED"];

export function History() {
  const { loading, items } = useActivity();
  const { status, setStatus, query, setQuery, filtered } = useActivityFilter(items);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-50">Activity Stream</h1>
          <p className="mt-1 text-slate-400">Past transactions and their validator consensus states.</p>
        </div>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search hash or method…"
          className="field max-w-xs"
        />
      </div>

      {/* filter chips */}
      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setStatus(f)}
            className={clsx(
              "rounded-full border px-3.5 py-1.5 text-xs font-semibold transition",
              status === f
                ? "border-accent-cyan/60 bg-accent-cyan/15 text-accent-cyan shadow-glow"
                : "border-white/10 bg-white/[0.03] text-slate-400 hover:border-white/25",
            )}
          >
            {f === "ALL" ? "All" : f.charAt(0) + f.slice(1).toLowerCase()}
          </button>
        ))}
      </div>

      <GlassCard>
        {loading ? (
          <div className="divide-y divide-white/5">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonRow key={i} />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16 text-center text-slate-500">
            <p className="text-lg">No activity matches your filters.</p>
            <p className="mt-1 text-sm">Try a different status or clear the search.</p>
          </div>
        ) : (
          <ul className="divide-y divide-white/5">
            <AnimatePresence initial={false}>
              {filtered.map((a, i) => (
                <motion.li
                  key={a.hash}
                  layout
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ delay: i * 0.03, type: "spring", stiffness: 300, damping: 26 }}
                  className="group flex items-center gap-4 py-4"
                >
                  {/* timeline node */}
                  <div className="relative flex flex-col items-center self-stretch">
                    <span
                      className={clsx(
                        "h-2.5 w-2.5 rounded-full",
                        a.status === "ACCEPTED" && "bg-status-accepted shadow-[0_0_10px_rgba(55,245,163,0.8)]",
                        a.status === "PENDING" && "bg-status-pending animate-glow-pulse",
                        a.status === "REJECTED" && "bg-status-rejected",
                      )}
                    />
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-100">{a.method}()</span>
                      <a
                        href={explorerTxUrl(a.hash)}
                        target="_blank"
                        rel="noreferrer"
                        className="font-mono text-xs text-accent-cyan opacity-0 transition group-hover:opacity-100 hover:underline"
                      >
                        {shortHash(a.hash)} ↗
                      </a>
                    </div>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {relativeTime(a.timestamp)}
                      {a.block ? ` · block ${a.block}` : ""} · validators {a.validators.agree}/{a.validators.total}
                    </p>
                  </div>

                  {/* consensus meter */}
                  <div className="hidden w-24 sm:block">
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                      <div
                        className={clsx(
                          "h-full rounded-full",
                          a.status === "ACCEPTED" && "bg-status-accepted",
                          a.status === "PENDING" && "bg-status-pending",
                          a.status === "REJECTED" && "bg-status-rejected",
                        )}
                        style={{ width: `${(a.validators.agree / a.validators.total) * 100}%` }}
                      />
                    </div>
                  </div>

                  <StatusBadge status={a.status} />
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        )}
      </GlassCard>
    </div>
  );
}
