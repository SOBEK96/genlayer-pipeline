import type { Abi } from "viem";
import { env } from "./env";

/**
 * Example GenLayer intelligent-contract ABI used by the Action Hub.
 * Replace with your deployed contract's ABI (or import a generated one).
 * `submitClaim` is a representative write method that triggers validator
 * consensus; `getClaimCount` is a representative view.
 */
export const demoAbi = [
  {
    type: "function",
    name: "submitClaim",
    stateMutability: "nonpayable",
    inputs: [
      { name: "document", type: "string" },
      { name: "priority", type: "uint8" },
    ],
    outputs: [{ name: "id", type: "uint256" }],
  },
  {
    type: "function",
    name: "getClaimCount",
    stateMutability: "view",
    inputs: [],
    outputs: [{ name: "", type: "uint256" }],
  },
] as const satisfies Abi;

/**
 * A known-good GenLayer Studionet deployment (AIPatentGuard) used as a fallback
 * when no address is configured — e.g. a fresh Vercel deploy where
 * VITE_CONTRACT_ADDRESS was never set in the dashboard. This keeps the Action
 * Hub functional out-of-the-box; override it via env or the in-app settings.
 */
export const DEFAULT_CONTRACT_ADDRESS =
  "0x032fd9BD3b79178A26e1872F1e214BD4b16bD23b" as const;

const HEX_ADDRESS = /^0x[0-9a-fA-F]{40}$/;

/** True when `value` is a syntactically valid EVM address. */
export function isAddress(value: string | null | undefined): value is `0x${string}` {
  return typeof value === "string" && HEX_ADDRESS.test(value);
}

/**
 * The env-configured contract address, or the default Studionet deployment when
 * the env var is missing/invalid. Always resolves to a usable address so the UI
 * never blocks the user on a missing VITE_CONTRACT_ADDRESS.
 */
export const contractAddress: `0x${string}` = isAddress(env.contractAddress)
  ? env.contractAddress
  : DEFAULT_CONTRACT_ADDRESS;

/** Whether the active default came from an explicit env var (vs. the fallback). */
export const isContractAddressFromEnv = isAddress(env.contractAddress);
