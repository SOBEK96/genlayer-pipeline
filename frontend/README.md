# GenLayer · Spatial Console

Immersive **3D glassmorphic Web3 frontend** for GenLayer intelligent contracts.
React + TypeScript + Vite + Tailwind + Framer Motion, wallet + contract layer on
**wagmi v2 / viem**.

## Quick start

```bash
cd frontend               # from the PipeLine repository root
cp .env.example .env      # fill in chain id / RPC / WalletConnect projectId
npm install
npm run dev               # http://localhost:5173
npm run build             # typecheck + production bundle
```

## Architecture

```
src/
├── components/
│   ├── 3d/     GlassCard, TiltCard (mouse-driven perspective), AmbientGlow, Skeleton
│   ├── web3/   ConnectButton (picker modal), NetworkBadge, AccountPill
│   └── ui/     Layout, Spinner, StatusBadge, ToastViewport
├── context/    Web3Provider (wagmi+react-query), ToastContext (glass toasts)
├── hooks/      useTilt, useWallet, useNetwork, useContractAction, useActivity
├── lib/        wagmi, chains, env, errors, format, contract, cx
└── views/      Dashboard, ActionHub, History
```

## Feature map

| Requirement | Where |
|---|---|
| Frosted glass + multi-layer borders + inner sheen | `index.css` `.glass`, `GlassCard` |
| 3D tilt / perspective on mouse move + cursor glare | `hooks/useTilt.ts`, `3d/TiltCard.tsx` |
| Ambient glow / floating orbs / depth grid | `3d/AmbientGlow.tsx` |
| MetaMask / WalletConnect / injected | `lib/wagmi.ts`, `web3/ConnectButton.tsx` |
| Network detection + auto chain-switch | `hooks/useNetwork.ts`, `web3/NetworkBadge.tsx` |
| Reactive balance / account listeners | `hooks/useWallet.ts` |
| Gas estimation + receipt tracking | `hooks/useContractAction.ts` |
| Spatial dashboard / action hub / history | `views/*` |
| 3D skeletons + consensus spinner | `3d/Skeleton.tsx`, `ui/Spinner.tsx` |
| Glass toasts w/ tx hash + copy | `context/ToastContext.tsx`, `ui/ToastViewport.tsx` |
| Raw error → actionable message | `lib/errors.ts` |
| Consensus states ACCEPTED/PENDING/REJECTED | `ui/StatusBadge.tsx`, `views/History.tsx` |

## Wiring a real contract

1. Set `VITE_CONTRACT_ADDRESS` in `.env`.
2. Replace `demoAbi` in `src/lib/contract.ts` with your deployed ABI.
3. In `views/ActionHub.tsx`, point `execute({ functionName, args })` at your method.
4. In `hooks/useActivity.ts`, swap the seed data for `usePublicClient().getLogs(...)`
   or a GenLayer indexer query.

## Security & responsiveness

- **No secrets in code** — only public `VITE_` config; `.env` is git-ignored.
- Fully responsive (mobile drawer nav → desktop bar); dark-mode base.
