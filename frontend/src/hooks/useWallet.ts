import { useMemo } from "react";
import {
  useAccount,
  useBalance,
  useConnect,
  useDisconnect,
  type Connector,
} from "wagmi";
import { env } from "@/lib/env";
import { formatBalance, shortAddress } from "@/lib/format";

/**
 * Clean, reactive wallet facade over wagmi. Exposes account, connection state,
 * live native balance, and connect/disconnect actions with the available
 * connectors (MetaMask / WalletConnect / injected).
 */
export function useWallet() {
  const { address, isConnected, isConnecting, chainId, connector, status } = useAccount();
  const { connectors, connectAsync, isPending: isConnectPending, error: connectError } =
    useConnect();
  const { disconnect } = useDisconnect();

  const { data: balance, isLoading: balanceLoading } = useBalance({
    address,
    query: { enabled: Boolean(address), refetchInterval: 15_000 },
  });

  const formattedBalance = useMemo(
    () => formatBalance(balance?.value, balance?.decimals ?? env.nativeDecimals),
    [balance],
  );

  const connect = async (c: Connector) => {
    await connectAsync({ connector: c });
  };

  return {
    address,
    displayAddress: shortAddress(address),
    isConnected,
    isConnecting: isConnecting || isConnectPending,
    status,
    chainId,
    connector,
    connectors,
    connect,
    disconnect,
    connectError,
    balance,
    formattedBalance,
    balanceSymbol: balance?.symbol ?? env.nativeSymbol,
    balanceLoading,
  };
}
