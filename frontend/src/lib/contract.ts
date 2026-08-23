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

export const contractAddress: `0x${string}` | undefined =
  env.contractAddress && env.contractAddress.startsWith("0x")
    ? (env.contractAddress as `0x${string}`)
    : undefined;
