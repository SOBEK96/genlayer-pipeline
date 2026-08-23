import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { TiltCard } from "@/components/3d/TiltCard";
import { GlassCard } from "@/components/3d/GlassCard";
import { Spinner } from "@/components/ui/Spinner";
import { NetworkBadge } from "@/components/web3/NetworkBadge";
import { ConnectButton } from "@/components/web3/ConnectButton";
import { ContractSettings } from "@/components/web3/ContractSettings";
import { useWallet } from "@/hooks/useWallet";
import { useNetwork } from "@/hooks/useNetwork";
import { useContractAction } from "@/hooks/useContractAction";
import { useContractAddress } from "@/hooks/useContractAddress";
import { demoAbi } from "@/lib/contract";
import { clsx } from "@/lib/cx";

interface FormState {
  document: string;
  priority: number;
}

function validate({ document, priority }: FormState) {
  const errors: Partial<Record<keyof FormState, string>> = {};
  if (!document.trim()) errors.document = "A document payload is required.";
  else if (document.trim().length < 8) errors.document = "Payload must be at least 8 characters.";
  else if (document.length > 2000) errors.document = "Payload exceeds 2000 characters.";
  if (priority < 1 || priority > 5) errors.priority = "Priority must be between 1 and 5.";
  return errors;
}

export function ActionHub() {
  const { isConnected } = useWallet();
  const { isCorrectNetwork } = useNetwork();
  const [form, setForm] = useState<FormState>({ document: "", priority: 3 });
  const [touched, setTouched] = useState<Partial<Record<keyof FormState, boolean>>>({});

  const contract = useContractAddress();
  const action = useContractAction({ address: contract.address, abi: demoAbi });
  const errors = useMemo(() => validate(form), [form]);
  const isValid = Object.keys(errors).length === 0;

  const blockers: string[] = [];
  if (!isConnected) blockers.push("Connect a wallet");
  if (isConnected && !isCorrectNetwork) blockers.push("Switch to the target network");

  const canSubmit = isValid && blockers.length === 0 && !action.isBusy;

  const submit = async () => {
    if (!canSubmit) return;
    try {
      await action.execute({ functionName: "submitClaim", args: [form.document, form.priority] });
    } catch {
      /* toast already surfaced the friendly error */
    }
  };

  const set = <K extends keyof FormState>(k: K, v: FormState[K]) => setForm((f) => ({ ...f, [k]: v }));
  const showErr = (k: keyof FormState) => touched[k] && errors[k];

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1.4fr_1fr]">
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-50">Action Hub</h1>
          <p className="mt-1 text-slate-400">
            Submit an intelligent-contract action. Inputs validate live; gas is estimated before you sign.
          </p>
        </div>

        <TiltCard max={5} glow>
          <div className="space-y-5">
            {/* document */}
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-300">Document payload</label>
              <textarea
                rows={5}
                value={form.document}
                onChange={(e) => set("document", e.target.value)}
                onBlur={() => setTouched((t) => ({ ...t, document: true }))}
                placeholder="Paste the claim / document to submit for validator consensus…"
                className={clsx(
                  "field resize-none font-mono text-sm",
                  showErr("document")
                    ? "border-status-rejected/60 focus:border-status-rejected focus:ring-status-rejected/20"
                    : form.document && !errors.document && "border-accent-cyan/50",
                )}
              />
              <div className="mt-1 flex justify-between text-xs">
                <span className={clsx(showErr("document") ? "text-status-rejected" : "text-transparent")}>
                  {errors.document ?? "."}
                </span>
                <span className="text-slate-500">{form.document.length}/2000</span>
              </div>
            </div>

            {/* priority — dynamic segmented control */}
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-300">Priority</label>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => set("priority", p)}
                    className={clsx(
                      "h-11 flex-1 rounded-xl border text-sm font-semibold transition",
                      form.priority === p
                        ? "border-accent-cyan/60 bg-accent-cyan/15 text-accent-cyan shadow-glow"
                        : "border-white/10 bg-white/[0.03] text-slate-400 hover:border-white/25",
                    )}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            {/* actions */}
            <div className="flex flex-wrap items-center gap-3 pt-1">
              <button className="btn-primary" onClick={submit} disabled={!canSubmit}>
                {action.isBusy ? <Spinner size={18} /> : null}
                {action.status === "signing"
                  ? "Confirm in wallet…"
                  : action.status === "pending"
                    ? "Awaiting consensus…"
                    : "Submit action"}
              </button>
              <button
                className="btn-ghost"
                disabled={!isValid || action.isBusy}
                onClick={() =>
                  action
                    .estimateGas({ functionName: "submitClaim", args: [form.document, form.priority] })
                    .catch(() => {})
                }
              >
                Estimate gas
              </button>
              {action.gas !== undefined && (
                <span className="text-xs text-slate-400">
                  est. gas: <span className="font-mono text-slate-200">{action.gas.toString()}</span>
                </span>
              )}
            </div>

            {blockers.length > 0 && (
              <div className="rounded-xl border border-status-pending/30 bg-status-pending/10 p-3 text-sm text-status-pending">
                Before submitting: {blockers.join(" · ")}.
              </div>
            )}
          </div>
        </TiltCard>
      </div>

      {/* live feedback panel */}
      <div className="space-y-6">
        <GlassCard>
          <h3 className="text-sm font-semibold uppercase tracking-widest text-slate-500">Connection</h3>
          <div className="mt-4 space-y-3">
            <ConnectButton />
            <NetworkBadge />
          </div>
        </GlassCard>

        <GlassCard>
          <ContractSettings
            address={contract.address}
            source={contract.source}
            isCustom={contract.isCustom}
            onSave={contract.save}
            onClear={contract.clear}
          />
        </GlassCard>

        <GlassCard glow>
          <h3 className="text-sm font-semibold uppercase tracking-widest text-slate-500">Transaction state</h3>
          <StateTimeline status={action.status} />
          {action.hash && (
            <a
              href={action.explorerUrl}
              target="_blank"
              rel="noreferrer"
              className="mt-3 block break-all font-mono text-xs text-accent-cyan hover:underline"
            >
              {action.hash} ↗
            </a>
          )}
          {action.receipt && (
            <p className="mt-2 text-xs text-slate-400">
              Block {action.receipt.blockNumber.toString()} · gas used{" "}
              <span className="font-mono">{action.receipt.gasUsed.toString()}</span>
            </p>
          )}
        </GlassCard>
      </div>
    </div>
  );
}

const STEPS = [
  { key: "estimating", label: "Estimating gas" },
  { key: "signing", label: "Awaiting signature" },
  { key: "pending", label: "Validator consensus" },
  { key: "success", label: "Confirmed" },
] as const;

function StateTimeline({ status }: { status: string }) {
  const order = ["idle", "estimating", "signing", "pending", "success"];
  const current = order.indexOf(status === "error" ? "idle" : status);
  return (
    <ol className="mt-4 space-y-3">
      {STEPS.map((s, i) => {
        const stepIdx = order.indexOf(s.key);
        const done = current > stepIdx;
        const active = status === s.key;
        return (
          <li key={s.key} className="flex items-center gap-3">
            <span
              className={clsx(
                "flex h-6 w-6 items-center justify-center rounded-full border text-xs",
                done && "border-status-accepted/50 bg-status-accepted/15 text-status-accepted",
                active && "border-accent-cyan/60 bg-accent-cyan/15 text-accent-cyan",
                !done && !active && "border-white/10 text-slate-600",
              )}
            >
              {active ? (
                <motion.span
                  className="h-2 w-2 rounded-full bg-accent-cyan"
                  animate={{ scale: [1, 1.6, 1] }}
                  transition={{ repeat: Infinity, duration: 1.2 }}
                />
              ) : done ? (
                "✓"
              ) : (
                i + 1
              )}
            </span>
            <span className={clsx("text-sm", active ? "text-slate-100" : done ? "text-slate-300" : "text-slate-600")}>
              {s.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
