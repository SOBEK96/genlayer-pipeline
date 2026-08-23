import { formatUnits } from "viem";

/** 0x1234…abcd */
export function shortAddress(addr?: string, lead = 6, tail = 4): string {
  if (!addr) return "—";
  if (addr.length <= lead + tail) return addr;
  return `${addr.slice(0, lead)}…${addr.slice(-tail)}`;
}

/** Human-friendly balance with a fixed precision, trimming trailing zeros. */
export function formatBalance(
  value: bigint | undefined,
  decimals = 18,
  precision = 4,
): string {
  if (value === undefined) return "0";
  const s = formatUnits(value, decimals);
  const [int, frac = ""] = s.split(".");
  const trimmed = frac.slice(0, precision).replace(/0+$/, "");
  return trimmed ? `${int}.${trimmed}` : int;
}

export function shortHash(hash?: string): string {
  return shortAddress(hash, 10, 8);
}

export function relativeTime(ts: number): string {
  const diff = Math.max(0, Date.now() - ts);
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}
