import { useCallback, useState } from "react";
import { useAccount, usePublicClient, useWriteContract } from "wagmi";
import type { Abi, Hash, TransactionReceipt } from "viem";
import { useToast } from "@/context/ToastContext";
import { translateError } from "@/lib/errors";
import { explorerTxUrl } from "@/lib/chains";
import { shortHash } from "@/lib/format";

export type ActionStatus =
  | "idle"
  | "estimating"
  | "signing"
  | "pending"
  | "success"
  | "error";

interface ExecuteArgs {
  functionName: string;
  args?: readonly unknown[];
  value?: bigint;
}

interface UseContractActionOpts {
  address?: `0x${string}`;
  abi: Abi;
}

/**
 * Generic write-path for any contract call:
 *   estimate gas → sign → submit → track receipt → toast + friendly errors.
 * Returns reactive status plus the resolved hash / receipt.
 */
export function useContractAction({ address, abi }: UseContractActionOpts) {
  const { address: account } = useAccount();
  const publicClient = usePublicClient();
  const { writeContractAsync } = useWriteContract();
  const toast = useToast();

  const [status, setStatus] = useState<ActionStatus>("idle");
  const [hash, setHash] = useState<Hash>();
  const [receipt, setReceipt] = useState<TransactionReceipt>();
  const [gas, setGas] = useState<bigint>();

  const reset = useCallback(() => {
    setStatus("idle");
    setHash(undefined);
    setReceipt(undefined);
    setGas(undefined);
  }, []);

  /** Pre-flight gas estimate (also acts as an early revert check). */
  const estimateGas = useCallback(
    async ({ functionName, args = [], value }: ExecuteArgs) => {
      if (!publicClient || !address || !account) return undefined;
      setStatus("estimating");
      const estimate = await publicClient.estimateContractGas({
        address,
        abi,
        functionName,
        args,
        value,
        account,
      });
      setGas(estimate);
      setStatus("idle");
      return estimate;
    },
    [publicClient, address, account, abi],
  );

  const execute = useCallback(
    async ({ functionName, args = [], value }: ExecuteArgs) => {
      if (!address) throw new Error("No contract address configured.");
      if (!account) throw new Error("Connect a wallet first.");
      if (!publicClient) throw new Error("No RPC client available.");

      const toastId = toast.push({
        variant: "pending",
        title: `Preparing ${functionName}()`,
        message: "Estimating gas…",
      });

      try {
        // 1. gas estimation (surfaces reverts before the wallet prompt)
        setStatus("estimating");
        let gasLimit: bigint | undefined;
        try {
          gasLimit = await publicClient.estimateContractGas({
            address,
            abi,
            functionName,
            args,
            value,
            account,
          });
          setGas(gasLimit);
        } catch {
          // Non-fatal: let the wallet estimate. Reverts still caught on send.
          gasLimit = undefined;
        }

        // 2. sign + submit
        setStatus("signing");
        toast.update(toastId, { title: `Confirm ${functionName}()`, message: "Approve in your wallet…" });
        const txHash = await writeContractAsync({
          address,
          abi,
          functionName,
          args,
          value,
          ...(gasLimit ? { gas: (gasLimit * 12n) / 10n } : {}), // +20% headroom
        });
        setHash(txHash);

        // 3. track receipt
        setStatus("pending");
        toast.update(toastId, {
          variant: "pending",
          title: "Awaiting consensus",
          message: `Submitted ${shortHash(txHash)} — waiting for validators…`,
          hash: txHash,
        });

        const rcpt = await publicClient.waitForTransactionReceipt({ hash: txHash });
        setReceipt(rcpt);

        if (rcpt.status === "reverted") {
          setStatus("error");
          toast.update(toastId, {
            variant: "error",
            title: "Transaction reverted",
            message: "The contract rejected the transaction on-chain.",
            hash: txHash,
            duration: 9000,
          });
          return { hash: txHash, receipt: rcpt, ok: false as const };
        }

        setStatus("success");
        toast.update(toastId, {
          variant: "success",
          title: "Confirmed by consensus",
          message: `${functionName}() accepted in block ${rcpt.blockNumber}.`,
          hash: txHash,
          duration: 8000,
        });
        return { hash: txHash, receipt: rcpt, ok: true as const };
      } catch (err) {
        const friendly = translateError(err);
        setStatus("error");
        toast.update(toastId, {
          variant: friendly.cancelled ? "info" : "error",
          title: friendly.title,
          message: friendly.detail,
          duration: friendly.cancelled ? 4000 : 9000,
          hash: undefined,
        });
        throw err;
      }
    },
    [address, account, publicClient, abi, writeContractAsync, toast],
  );

  return {
    execute,
    estimateGas,
    reset,
    status,
    hash,
    receipt,
    gas,
    explorerUrl: hash ? explorerTxUrl(hash) : undefined,
    isBusy: status === "estimating" || status === "signing" || status === "pending",
  };
}
