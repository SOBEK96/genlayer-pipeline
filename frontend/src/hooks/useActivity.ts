import { useEffect, useMemo, useState } from "react";
import type { ConsensusStatus } from "@/components/ui/StatusBadge";

export interface Activity {
  hash: string;
  method: string;
  status: ConsensusStatus;
  timestamp: number;
  validators: { agree: number; total: number };
  block?: number;
}

/**
 * Activity stream source.
 *
 * In production this reads from contract event logs (viem `getLogs` /
 * `watchContractEvent`) or a GenLayer indexer. Here it returns representative
 * seed data so the History view is fully interactive out of the box. Swap the
 * body for a real `usePublicClient().getLogs(...)` query when wiring a contract.
 */
export function useActivity() {
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<Activity[]>([]);

  useEffect(() => {
    const t = setTimeout(() => {
      setItems(SEED);
      setLoading(false);
    }, 650); // simulate an on-chain/indexer fetch
    return () => clearTimeout(t);
  }, []);

  const prepend = (a: Activity) => setItems((prev) => [a, ...prev]);

  return { loading, items, prepend };
}

/** Client-side filter + search over the activity stream. */
export function useActivityFilter(items: Activity[]) {
  const [status, setStatus] = useState<ConsensusStatus | "ALL">("ALL");
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((a) => {
      const matchStatus = status === "ALL" || a.status === status;
      const matchQuery = !q || a.hash.toLowerCase().includes(q) || a.method.toLowerCase().includes(q);
      return matchStatus && matchQuery;
    });
  }, [items, status, query]);

  return { status, setStatus, query, setQuery, filtered };
}

const now = Date.now();
const SEED: Activity[] = [
  { hash: "0x9f2a4c1de77b0aa3c5e1b0f42a9c8e73d1b5f6a2c4e8d0b1a3f7c9e2d4b6a8c10", method: "submitClaim", status: "ACCEPTED", timestamp: now - 1000 * 60 * 3, validators: { agree: 5, total: 5 }, block: 184213 },
  { hash: "0x3b8e1f0a2c4d6e8b0a1c3e5d7f9b1a3c5e7d9f1b3a5c7e9d1f3b5a7c9e1d3f50", method: "submitClaim", status: "PENDING", timestamp: now - 1000 * 60 * 1, validators: { agree: 3, total: 5 } },
  { hash: "0x7d1c3a5e9f2b4d6a8c0e2f4b6d8a0c2e4f6b8d0a2c4e6f8b0d2a4c6e8f0b2d40", method: "appeal", status: "REJECTED", timestamp: now - 1000 * 60 * 22, validators: { agree: 1, total: 5 }, block: 184190 },
  { hash: "0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a20", method: "submitClaim", status: "ACCEPTED", timestamp: now - 1000 * 60 * 60 * 2, validators: { agree: 4, total: 5 }, block: 183980 },
  { hash: "0x5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e60", method: "deploy", status: "ACCEPTED", timestamp: now - 1000 * 60 * 60 * 26, validators: { agree: 5, total: 5 }, block: 182110 },
];
