import { clsx } from "@/lib/cx";

interface SpinnerProps {
  size?: number;
  className?: string;
  label?: string;
}

/** Dual-ring consensus spinner with a glowing core. */
export function Spinner({ size = 28, className, label }: SpinnerProps) {
  return (
    <div className={clsx("inline-flex items-center gap-3", className)} role="status" aria-live="polite">
      <span className="relative inline-block" style={{ width: size, height: size }}>
        <span className="absolute inset-0 rounded-full border-2 border-white/10" />
        <span className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-accent-cyan border-r-accent-violet" />
        <span className="absolute inset-1.5 animate-spin-slow rounded-full border border-transparent border-b-accent-magenta" />
        <span className="absolute inset-0 m-auto h-1.5 w-1.5 rounded-full bg-accent-cyan shadow-glow" />
      </span>
      {label && <span className="text-sm text-slate-400">{label}</span>}
    </div>
  );
}
