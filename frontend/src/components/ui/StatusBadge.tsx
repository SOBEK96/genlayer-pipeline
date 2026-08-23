import { clsx } from "@/lib/cx";

export type ConsensusStatus = "ACCEPTED" | "PENDING" | "REJECTED";

const MAP: Record<ConsensusStatus, { dot: string; text: string; ring: string; label: string }> = {
  ACCEPTED: { dot: "bg-status-accepted", text: "text-status-accepted", ring: "border-status-accepted/30 bg-status-accepted/10", label: "Accepted" },
  PENDING: { dot: "bg-status-pending", text: "text-status-pending", ring: "border-status-pending/30 bg-status-pending/10", label: "Pending" },
  REJECTED: { dot: "bg-status-rejected", text: "text-status-rejected", ring: "border-status-rejected/30 bg-status-rejected/10", label: "Rejected" },
};

export function StatusBadge({ status, className }: { status: ConsensusStatus; className?: string }) {
  const s = MAP[status];
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold",
        s.ring,
        s.text,
        className,
      )}
    >
      <span className={clsx("h-1.5 w-1.5 rounded-full", s.dot, status === "PENDING" && "animate-glow-pulse")} />
      {s.label}
    </span>
  );
}
