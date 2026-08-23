import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx } from "@/lib/cx";

interface Step {
  key: string;
  label: string;
  title: string;
  body: string;
  code: string[];
}

const STEPS: Step[] = [
  {
    key: "install",
    label: "Install",
    title: "Install the CLI + toolchain",
    body: "One editable install pulls the console scripts and the GenLayer toolchain the lint/test/build stages shell out to.",
    code: ["# from the PipeLine workspace", "make install", "# → pip install -e '.[toolchain]'"],
  },
  {
    key: "configure",
    label: "Configure",
    title: "Point it at your project",
    body: "Copy .env.example and (optionally) drop a pipeline.toml in the target repo. Anything you omit falls back to conventions and auto-discovery.",
    code: ["cp .env.example .env", "# set VITE_/GENLAYER_ vars", "# optional: config/pipeline.example.toml"],
  },
  {
    key: "run",
    label: "Run CI",
    title: "Run the full local pipeline",
    body: "make ci runs lint → test → build against your target — exactly what GitHub runs. Each stage is gated on the previous.",
    code: ["make ci                       # target = this dir", "make ci TARGET=/path/to/project"],
  },
  {
    key: "deploy",
    label: "Deploy",
    title: "Deploy to Studionet",
    body: "The opt-in deploy stage promotes a verified contract, records it in the ledger, and rolls back automatically if post-deploy checks fail.",
    code: ["make deploy                   # guardrailed", "make ledger                   # show live address"],
  },
];

/** Interactive stepper explaining install → configure → run → deploy. */
export function HowItWorks() {
  const [active, setActive] = useState(0);
  const step = STEPS[active];

  return (
    <section id="how-it-works" className="scroll-mt-24 space-y-8">
      <div className="text-center">
        <h2 className="text-3xl font-extrabold tracking-tight text-slate-50 sm:text-4xl">
          How it <span className="text-gradient">works</span>
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-slate-400">
          Four steps from a fresh checkout to a live, verified deployment.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        {/* step rail */}
        <ol className="space-y-3">
          {STEPS.map((s, i) => {
            const isActive = i === active;
            return (
              <li key={s.key}>
                <button
                  type="button"
                  onClick={() => setActive(i)}
                  className={clsx(
                    "flex w-full items-center gap-4 rounded-2xl border px-4 py-4 text-left transition-all",
                    isActive
                      ? "border-accent-cyan/40 bg-white/[0.06] shadow-glow"
                      : "border-white/10 bg-white/[0.02] hover:border-white/20",
                  )}
                >
                  <span
                    className={clsx(
                      "flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border font-mono text-sm font-bold",
                      isActive
                        ? "border-accent-cyan/50 bg-accent-cyan/15 text-accent-cyan"
                        : "border-white/10 text-slate-500",
                    )}
                  >
                    {i + 1}
                  </span>
                  <div>
                    <p className={clsx("text-sm font-semibold", isActive ? "text-slate-50" : "text-slate-300")}>
                      {s.label}
                    </p>
                    <p className="text-xs text-slate-500">{s.title}</p>
                  </div>
                </button>
              </li>
            );
          })}
        </ol>

        {/* detail panel */}
        <div className="relative">
          <div className="ambient-ring" aria-hidden />
          <div className="glass h-full p-6">
            <AnimatePresence mode="wait">
              <motion.div
                key={step.key}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.22 }}
              >
                <h3 className="text-xl font-bold text-slate-50">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">{step.body}</p>

                <div className="mt-5 overflow-hidden rounded-xl border border-white/10 bg-base-900/70">
                  <div className="flex items-center gap-1.5 border-b border-white/5 px-4 py-2.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-status-rejected/70" />
                    <span className="h-2.5 w-2.5 rounded-full bg-status-pending/70" />
                    <span className="h-2.5 w-2.5 rounded-full bg-status-accepted/70" />
                    <span className="ml-2 font-mono text-xs text-slate-500">terminal</span>
                  </div>
                  <pre className="overflow-x-auto px-4 py-4 font-mono text-sm leading-relaxed text-slate-200">
                    {step.code.map((line, i) => (
                      <div key={i} className={clsx(line.startsWith("#") && "text-slate-500")}>
                        {!line.startsWith("#") && <span className="select-none text-accent-cyan">$ </span>}
                        {line}
                      </div>
                    ))}
                  </pre>
                </div>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}
