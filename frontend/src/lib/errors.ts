import { BaseError } from "viem";

export interface FriendlyError {
  title: string;
  detail: string;
  /** true when the user themselves cancelled — not a real failure to alert on. */
  cancelled: boolean;
}

/**
 * Translate raw blockchain / validator / wallet errors into clear, actionable
 * user messages. Walks viem's error cause chain and falls back to pattern
 * matching so nothing ever surfaces a raw hex blob to the user.
 */
export function translateError(err: unknown): FriendlyError {
  const raw = extractMessage(err).toLowerCase();

  // User cancelled in wallet
  if (/user rejected|user denied|rejected the request|4001/.test(raw)) {
    return {
      title: "Request cancelled",
      detail: "You dismissed the request in your wallet. No transaction was sent.",
      cancelled: true,
    };
  }

  if (/insufficient funds|insufficient balance|exceeds balance/.test(raw)) {
    return {
      title: "Insufficient balance",
      detail: "Your account doesn't have enough to cover the amount plus gas fees.",
      cancelled: false,
    };
  }

  if (/chain mismatch|does not match the target chain|wrong network|unsupported chain/.test(raw)) {
    return {
      title: "Wrong network",
      detail: "Your wallet is on a different network. Switch to the target chain and retry.",
      cancelled: false,
    };
  }

  if (/nonce too low|nonce has already been used|replacement transaction underpriced/.test(raw)) {
    return {
      title: "Transaction conflict",
      detail: "A pending transaction is blocking this one. Wait for it to settle, then retry.",
      cancelled: false,
    };
  }

  if (/gas required exceeds|out of gas|intrinsic gas too low|gas limit/.test(raw)) {
    return {
      title: "Gas estimation failed",
      detail: "The transaction would run out of gas — it may revert on-chain. Check your inputs.",
      cancelled: false,
    };
  }

  // Contract / validator revert — surface the reason if present
  const revert = extractRevertReason(err);
  if (revert) {
    return {
      title: "Contract rejected the call",
      detail: revert,
      cancelled: false,
    };
  }

  if (/consensus|validator|disagree|no majority/.test(raw)) {
    return {
      title: "Validator consensus not reached",
      detail: "GenLayer validators did not agree on a result. This can be transient — retry shortly.",
      cancelled: false,
    };
  }

  if (/timeout|timed out|deadline/.test(raw)) {
    return {
      title: "Request timed out",
      detail: "The network took too long to respond. Check your connection and try again.",
      cancelled: false,
    };
  }

  if (/connector not found|no provider|no ethereum|not installed/.test(raw)) {
    return {
      title: "No wallet detected",
      detail: "Install MetaMask (or another EVM wallet), or connect via WalletConnect.",
      cancelled: false,
    };
  }

  return {
    title: "Something went wrong",
    detail: humanizeFallback(err),
    cancelled: false,
  };
}

function extractMessage(err: unknown): string {
  if (err instanceof BaseError) return `${err.shortMessage} ${err.details ?? ""} ${err.message}`;
  if (err instanceof Error) return err.message;
  if (typeof err === "string") return err;
  try {
    return JSON.stringify(err);
  } catch {
    return String(err);
  }
}

function extractRevertReason(err: unknown): string | null {
  if (err instanceof BaseError) {
    // viem exposes a walk() to find a specific error in the cause chain
    const revert = err.walk(
      (e) => (e as { name?: string })?.name === "ContractFunctionRevertedError",
    ) as { reason?: string; shortMessage?: string } | null;
    if (revert?.reason) return revert.reason;
    if (revert?.shortMessage) return revert.shortMessage;
    // Some reverts carry the reason in shortMessage of the top error
    const m = err.shortMessage?.match(/reverted with(?: the following reason)?:?\s*(.+)/i);
    if (m) return m[1].trim();
  }
  return null;
}

function humanizeFallback(err: unknown): string {
  const msg = extractMessage(err).trim();
  // Never dump a giant blob; take the first sentence-ish chunk.
  const firstLine = msg.split("\n")[0].slice(0, 180);
  return firstLine || "An unexpected error occurred. Please try again.";
}
