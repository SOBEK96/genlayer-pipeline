import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Hero } from "@/components/sections/Hero";
import { PipelineFlow } from "@/components/sections/PipelineFlow";
import { FeatureGrid } from "@/components/sections/FeatureGrid";
import { HowItWorks } from "@/components/sections/HowItWorks";
import { Faq } from "@/components/sections/Faq";

/**
 * Public landing experience. Renders fully without a connected wallet so the
 * main content area is always rich — hero, pipeline flow, features, an
 * interactive how-it-works stepper, and an FAQ accordion.
 */
export function Home() {
  return (
    <div className="space-y-24 pb-8">
      <Hero />
      <PipelineFlow />
      <FeatureGrid />
      <HowItWorks />
      <Faq />

      {/* closing CTA */}
      <motion.section
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-60px" }}
        transition={{ type: "spring", stiffness: 220, damping: 24 }}
        className="relative"
      >
        <div className="ambient-ring" aria-hidden />
        <div className="glass overflow-hidden px-6 py-12 text-center sm:px-12">
          <h2 className="text-3xl font-extrabold tracking-tight text-slate-50 sm:text-4xl">
            Ready to run your first <span className="text-gradient">pipeline</span>?
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-slate-400">
            Open the Action Hub to submit an intelligent-contract action, or explore the live
            console dashboard once your wallet is connected.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link to="/action" className="btn-primary px-6 py-3 text-base">
              Open Action Hub
            </Link>
            <Link to="/dashboard" className="btn-ghost px-6 py-3 text-base">
              View Dashboard
            </Link>
          </div>
        </div>
      </motion.section>
    </div>
  );
}
