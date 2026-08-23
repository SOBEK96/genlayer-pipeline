import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { useNetwork } from "@/hooks/useNetwork";
import { env } from "@/lib/env";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, type: "spring", stiffness: 240, damping: 24 },
  }),
};

/** Landing hero: live network badge, gradient headline, and primary CTAs. */
export function Hero() {
  const { targetChain } = useNetwork();

  return (
    <section className="relative pt-10 sm:pt-16">
      <div className="mx-auto max-w-3xl text-center">
        <motion.div custom={0} variants={fadeUp} initial="hidden" animate="show">
          <span className="inline-flex items-center gap-2 rounded-full border border-status-accepted/30 bg-status-accepted/10 px-3.5 py-1.5 text-xs font-semibold text-status-accepted">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-status-accepted opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-status-accepted" />
            </span>
            {targetChain.name} · operational
          </span>
        </motion.div>

        <motion.h1
          custom={1}
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="mt-6 text-4xl font-extrabold leading-[1.05] tracking-tight text-slate-50 sm:text-6xl"
        >
          Ship GenLayer contracts
          <br />
          <span className="text-gradient">with total confidence.</span>
        </motion.h1>

        <motion.p
          custom={2}
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="mx-auto mt-5 max-w-xl text-base text-slate-400 sm:text-lg"
        >
          PipeLine is a target-agnostic CI/CD toolkit that lints, tests, validates, and
          deploys your intelligent contracts to {env.chainName} — with guardrails,
          rollback, and a full analytics report on every run.
        </motion.p>

        <motion.div
          custom={3}
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="mt-9 flex flex-wrap items-center justify-center gap-3"
        >
          <Link to="/action" className="btn-primary px-6 py-3 text-base">
            Launch Action Hub
          </Link>
          <a href="#how-it-works" className="btn-ghost px-6 py-3 text-base">
            How it works
          </a>
        </motion.div>

        <motion.div
          custom={4}
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="mx-auto mt-10 max-w-md"
        >
          <div className="glass flex items-center gap-3 px-4 py-3 text-left font-mono text-sm">
            <span className="select-none text-accent-cyan">$</span>
            <code className="text-slate-200">make ci</code>
            <span className="ml-auto rounded-md border border-status-accepted/30 bg-status-accepted/10 px-2 py-0.5 text-xs text-status-accepted">
              lint → test → build ✓
            </span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
