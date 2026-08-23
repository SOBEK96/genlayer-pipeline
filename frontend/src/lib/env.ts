/**
 * Centralised, typed access to VITE_ env vars. No secrets live here — only
 * public client config. Missing values fall back to safe placeholders so the
 * app renders in dev even before `.env` is filled in.
 */
const num = (v: string | undefined, fallback: number) => {
  const n = Number(v);
  return Number.isFinite(n) && n > 0 ? n : fallback;
};

export const env = {
  chainId: num(import.meta.env.VITE_CHAIN_ID, 4221),
  chainName: import.meta.env.VITE_CHAIN_NAME ?? "GenLayer Studionet",
  rpcUrl: import.meta.env.VITE_RPC_URL ?? "https://studio.genlayer.com/api",
  explorerUrl: import.meta.env.VITE_EXPLORER_URL ?? "https://studio.genlayer.com",
  nativeSymbol: import.meta.env.VITE_NATIVE_SYMBOL ?? "GEN",
  nativeDecimals: num(import.meta.env.VITE_NATIVE_DECIMALS, 18),
  walletConnectProjectId: import.meta.env.VITE_WALLETCONNECT_PROJECT_ID ?? "",
  contractAddress: (import.meta.env.VITE_CONTRACT_ADDRESS ?? "") as `0x${string}` | "",
} as const;

export const hasWalletConnect = env.walletConnectProjectId.length > 0;
