import { motion } from "framer-motion";
import { clsx } from "@/lib/cx";

interface Stage {
  n: number;
  name: string;
  tool: string;
  desc: string;
  accent: string;
}

const STAGES: Stage[] = [
  { n: 1, name: "Lint", tool: "genvm-lint", desc: "AST safety + SDK semantic validation", accent: "text-accent-cyan" },
  { n: 2, name: "Test", tool: "gltest", desc: "Direct-mode multi-agent suite", accent: "text-accent-violet" },
  { n: 3, name: "Build", tool: "schema + vite", desc: "ABI extraction + frontend build", accent: "text-accent-magenta" },
  { n: 4, name: "Deploy", tool: "genlayer", desc: "Guardrailed Studionet deploy", accent: "text-accent-lime" },
];

/** Horizontal visualization of the four gated pipeline stages. */
export function PipelineFlow() {
  return (
    <section className="relative">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STAGES.map((s, i) => (
          <motion.div
            key={s.n}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ delay: i * 0.1, type: "spring", stiffness: 220, damping: 22 }}
            className="group relative"
          >
            <div className="ambient-ring" aria-hidden />
            <div className="glass glass-hover h-full p-5">
              <div className="flex items-center justify-between">
                <span className={clsx("font-mono text-3xl font-extrabold", s.accent)}>
                  {String(s.n).padStart(2, "0")}
                </span>
                {i < STAGES.length - 1 && (
                  <span className="text-slate-600 transition-transform group-hover:translate-x-1">→</span>
                )}
              </div>
              <h3 className="mt-3 text-lg font-bold text-slate-50">{s.name}</h3>
              <p className="mt-0.5 font-mono text-xs text-slate-500">{s.tool}</p>
              <p className="mt-2 text-sm text-slate-400">{s.desc}</p>
            </div>
          </motion.div>
        ))}
      </div>
      <p className="mt-4 text-center text-xs text-slate-500">
        Every stage is gated — a downstream stage never starts unless every upstream stage is green.
      </p>
    </section>
  );
}
