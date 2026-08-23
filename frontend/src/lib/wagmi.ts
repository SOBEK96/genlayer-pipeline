import { createConfig, http } from "wagmi";
import { injected, metaMask, walletConnect } from "wagmi/connectors";
import { genLayerStudionet, supportedChains } from "./chains";
import { env, hasWalletConnect } from "./env";

/**
 * wagmi v2 config.
 * Connectors: generic injected EVM provider, MetaMask, and (when a projectId is
 * configured) WalletConnect. Transports use the env-driven RPC per chain.
 */
const connectors = [
  injected({ shimDisconnect: true }),
  metaMask(),
  ...(hasWalletConnect
    ? [
        walletConnect({
          projectId: env.walletConnectProjectId,
          showQrModal: true,
          metadata: {
            name: "GenLayer Spatial Console",
            description: "Immersive 3D Web3 console for GenLayer intelligent contracts",
            url: typeof window !== "undefined" ? window.location.origin : "https://genlayer.com",
            icons: [],
          },
        }),
      ]
    : []),
];

export const wagmiConfig = createConfig({
  chains: supportedChains,
  connectors,
  transports: {
    [genLayerStudionet.id]: http(env.rpcUrl),
  },
  ssr: false,
});

declare module "wagmi" {
  interface Register {
    config: typeof wagmiConfig;
  }
}
