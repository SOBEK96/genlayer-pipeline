import { useCallback, useMemo } from "react";
import { useAccount, useChainId, useSwitchChain } from "wagmi";
import { genLayerStudionet } from "@/lib/chains";
import { translateError } from "@/lib/errors";

/**
 * Real-time network state + automatic chain switching to GenLayer / Studionet.
 * `isCorrectNetwork` reacts to the wallet's active chain; `switchToTarget`
 * requests (and, on unknown chains, adds) the target network.
 */
export function useNetwork() {
  const { isConnected } = useAccount();
  const activeChainId = useChainId();
  const { switchChainAsync, isPending, chains } = useSwitchChain();

  const target = genLayerStudionet;
  const isCorrectNetwork = activeChainId === target.id;

  const switchToTarget = useCallback(async () => {
    try {
      await switchChainAsync({ chainId: target.id });
      return { ok: true as const };
    } catch (err) {
      return { ok: false as const, error: translateError(err) };
    }
  }, [switchChainAsync, target.id]);

  const activeChainName = useMemo(
    () => chains.find((c) => c.id === activeChainId)?.name ?? `Chain ${activeChainId}`,
    [chains, activeChainId],
  );

  return {
    isConnected,
    activeChainId,
    activeChainName,
    targetChain: target,
    isCorrectNetwork,
    isSwitching: isPending,
    switchToTarget,
  };
}
