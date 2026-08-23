import { Accordion, type AccordionItemData } from "@/components/ui/Accordion";

const FAQS: AccordionItemData[] = [
  {
    id: "what",
    question: "What is PipeLine?",
    answer:
      "PipeLine is a target-agnostic CI/CD and automated-testing toolkit for GenLayer intelligent contracts. It runs a gated four-stage pipeline — lint, test, build validation, and deployment — and ships as an installable CLI plus a Makefile of thin wrappers so your local run matches CI exactly.",
  },
  {
    id: "modify",
    question: "Do I have to modify my contract repository?",
    answer:
      "No. PipeLine runs against a target project without changing it. It resolves what to run from CLI args, an optional pipeline.toml, convention defaults, and auto-discovery — then writes every artifact back into its own workspace, leaving your target repo trace-free.",
  },
  {
    id: "prereqs",
    question: "What are the prerequisites?",
    answer:
      "Python 3.11+ for the stdlib-only core, Node.js for frontend build validation, and the GenLayer CLI (installed via npm) for the deploy stage. The lint and test stages use genvm-lint and gltest from the toolchain extra installed by 'make install'.",
  },
  {
    id: "networks",
    question: "Which networks are supported?",
    answer:
      "Deployments target GenLayer Studionet by default, with localnet and testnet selectable through configuration. The frontend chain definition is fully env-driven (chain id, RPC URL, explorer), so the same build can point at any GenLayer network without code changes.",
  },
  {
    id: "rollback",
    question: "How does deployment rollback work?",
    answer:
      "A durable JSON ledger records the current live address plus history. After deploying, PipeLine verifies the contract; if verification fails, the ledger pointer is never advanced, so clients keep talking to the last known-good address. The run logs the rollback decision it acted on.",
  },
  {
    id: "keys",
    question: "Are my private keys safe?",
    answer:
      "Keys live only in a git-ignored .env and are consumed through typed, validated env access — never hardcoded and never shipped to the browser. Only VITE_-prefixed public config reaches the client. Studionet is a gasless test network intended for throwaway deployer wallets.",
  },
  {
    id: "wallet",
    question: "How do I connect a wallet in the console?",
    answer:
      "Use the Connect Wallet button in the header. PipeLine supports MetaMask, any injected browser wallet, and WalletConnect (when a project id is configured). Once connected, the network badge lets you switch to the target chain in one click.",
  },
  {
    id: "ci",
    question: "Can I run PipeLine in GitHub Actions?",
    answer:
      "Yes — that is the design goal. 'make ci' is exactly what the workflow runs, and the pipeline includes a Stage 0 compliance pre-flight gate. Because the core is standard-library only, the CI environment installs and runs it quickly with no heavy dependency tree.",
  },
];

/** Accordion-style FAQ covering technical and deployment questions. */
export function Faq() {
  return (
    <section id="faq" className="scroll-mt-24">
      <div className="text-center">
        <h2 className="text-3xl font-extrabold tracking-tight text-slate-50 sm:text-4xl">
          Frequently asked <span className="text-gradient">questions</span>
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-slate-400">
          Everything you need to know before your first run and deployment.
        </p>
      </div>

      <div className="mx-auto mt-8 max-w-3xl">
        <Accordion items={FAQS} />
      </div>
    </section>
  );
}
