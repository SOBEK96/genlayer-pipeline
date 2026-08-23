import { motion } from "framer-motion";
import { TiltCard } from "@/components/3d/TiltCard";

interface Feature {
  icon: string;
  title: string;
  desc: string;
}

const FEATURES: Feature[] = [
  {
    icon: "◇",
    title: "Target-agnostic",
    desc: "No hardcoded project or contract references. Point it at any GenLayer repo and it resolves what to run dynamically.",
  },
  {
    icon: "⛨",
    title: "Guardrailed deploys",
    desc: "RPC security checks, env validation, and an error taxonomy stop unsafe or misconfigured deployments before they start.",
  },
  {
    icon: "⟲",
    title: "Automatic rollback",
    desc: "A durable deployment ledger tracks the live address. Failed verification never advances the pointer clients depend on.",
  },
  {
    icon: "◈",
    title: "Zero-trace runs",
    desc: "Runs against a target project but writes every artifact back into this workspace, leaving the target repo untouched.",
  },
  {
    icon: "▤",
    title: "Analytics report",
    desc: "Each run emits a full execution report — per-stage timings, test totals, deploy history, and failure alerts.",
  },
  {
    icon: "◎",
    title: "Stdlib-only core",
    desc: "The orchestration harness depends on zero third-party runtime packages, so it installs fast and runs anywhere.",
  },
];

/** Grid of interactive tilt feature cards. */
export function FeatureGrid() {
  return (
    <section className="space-y-8">
      <div className="text-center">
        <h2 className="text-3xl font-extrabold tracking-tight text-slate-50 sm:text-4xl">
          Built for serious <span className="text-gradient">contract delivery</span>
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-slate-400">
          Everything you need to take an intelligent contract from source to a verified,
          live deployment — safely and repeatably.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f, i) => (
          <motion.div
            key={f.title}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ delay: (i % 3) * 0.08, type: "spring", stiffness: 220, damping: 24 }}
          >
            <TiltCard max={7}>
              <div className="flex h-full flex-col">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-gradient-to-br from-accent-cyan/20 to-accent-violet/20 text-xl text-accent-cyan">
                  {f.icon}
                </span>
                <h3 className="mt-4 text-lg font-bold text-slate-50">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">{f.desc}</p>
              </div>
            </TiltCard>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
