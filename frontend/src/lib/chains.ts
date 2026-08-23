import { defineChain } from "viem";
import { env } from "./env";

/**
 * GenLayer / Studionet chain definition (EVM-compatible surface).
 * All fields are env-driven so the same build targets localnet / studionet /
 * testnet without code changes.
 */
export const genLayerStudionet = defineChain({
  id: env.chainId,
  name: env.chainName,
  nativeCurrency: {
    name: env.nativeSymbol,
    symbol: env.nativeSymbol,
    decimals: env.nativeDecimals,
  },
  rpcUrls: {
    default: { http: [env.rpcUrl] },
    public: { http: [env.rpcUrl] },
  },
  blockExplorers: {
    default: { name: "GenLayer Explorer", url: env.explorerUrl },
  },
  testnet: true,
});

export const supportedChains = [genLayerStudionet] as const;

export const explorerTxUrl = (hash: string) => `${env.explorerUrl}/tx/${hash}`;
export const explorerAddressUrl = (addr: string) => `${env.explorerUrl}/address/${addr}`;
