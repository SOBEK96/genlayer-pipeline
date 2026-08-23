import { useCallback, useState } from "react";
import {
  contractAddress as configuredAddress,
  isAddress,
  isContractAddressFromEnv,
} from "@/lib/contract";

const STORAGE_KEY = "pipeline.contractAddress";

export type AddressSource = "custom" | "env" | "default";

function readStored(): `0x${string}` | null {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return isAddress(v) ? v : null;
  } catch {
    return null;
  }
}

/**
 * Single source of truth for the active target contract address.
 * Resolution order: user override (persisted in localStorage) → env-configured
 * address → bundled default deployment. Always yields a valid address, so the
 * Action Hub never blocks on a missing VITE_CONTRACT_ADDRESS.
 */
export function useContractAddress() {
  const [custom, setCustom] = useState<`0x${string}` | null>(() => readStored());

  const address: `0x${string}` = custom ?? configuredAddress;
  const source: AddressSource = custom ? "custom" : isContractAddressFromEnv ? "env" : "default";

  const save = useCallback((value: string) => {
    const trimmed = value.trim();
    if (!isAddress(trimmed)) {
      return { ok: false as const, error: "Enter a valid address (0x followed by 40 hex characters)." };
    }
    try {
      localStorage.setItem(STORAGE_KEY, trimmed);
    } catch {
      /* storage unavailable (private mode) — keep the in-memory override */
    }
    setCustom(trimmed);
    return { ok: true as const };
  }, []);

  const clear = useCallback(() => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
    setCustom(null);
  }, []);

  return { address, source, isCustom: custom !== null, save, clear };
}
