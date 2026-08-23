/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CHAIN_ID: string;
  readonly VITE_CHAIN_NAME: string;
  readonly VITE_RPC_URL: string;
  readonly VITE_EXPLORER_URL: string;
  readonly VITE_NATIVE_SYMBOL: string;
  readonly VITE_NATIVE_DECIMALS: string;
  readonly VITE_WALLETCONNECT_PROJECT_ID: string;
  readonly VITE_CONTRACT_ADDRESS: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
