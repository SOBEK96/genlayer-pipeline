"""
Configuration guardrails for the GenLayer CI/CD Pipeline toolkit.

This module centralises every "fail loud, fail early" rule the pipeline enforces
so that no stage can start against a mis-configured environment. It implements
three families of guardrail requested in the Pipeline design brief:

  1. Environment-variable mappings  -> `REQUIRED_ENV` / `resolve_env()`
  2. RPC security                    -> `validate_rpc()`
  3. Error-handling protocols        -> `GuardrailError` + `require()`

Design principle: ZERO SILENT FAILURES.
Every check either returns a validated value or raises `GuardrailError` with an
actionable, secret-safe message. Nothing here ever prints a private key, and no
check is allowed to "warn and continue" for a security-relevant condition.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Iterable
from urllib.parse import urlparse

# --------------------------------------------------------------------------- #
# Error taxonomy                                                              #
# --------------------------------------------------------------------------- #
# The runner maps these onto process exit codes so CI can distinguish a
# mis-configuration (operator error, retry won't help) from a genuine stage
# failure (lint/test/build regression).


class GuardrailError(RuntimeError):
    """Raised when the environment is unsafe or incomplete for a stage.

    Distinct from a stage *failure*: a GuardrailError means we refused to run,
    not that the thing we ran failed.
    """


# --------------------------------------------------------------------------- #
# Environment-variable mapping                                                #
# --------------------------------------------------------------------------- #
# Each network chain-type maps to the env vars it needs. Deploy stages against
# a public network REQUIRE a signer key + RPC url; local direct-mode tests need
# nothing. Keys are chain-types accepted by gltest / genlayer.


@dataclass(frozen=True)
class EnvSpec:
    name: str
    required: bool = True
    secret: bool = False
    # Optional validation regex applied to the *value* (not logged on failure
    # for secrets).
    pattern: str | None = None
    help: str = ""


# Env vars consumed across the whole pipeline. `required` here means "required
# for a deploy against a remote chain"; the runner narrows this per-stage.
DEPLOY_ENV: tuple[EnvSpec, ...] = (
    EnvSpec(
        "GENLAYER_RPC_URL",
        required=True,
        pattern=r"^https?://",
        help="Full RPC endpoint, e.g. https://studio.genlayer.com/api",
    ),
    EnvSpec(
        "GENLAYER_CHAIN_TYPE",
        required=True,
        pattern=r"^(localnet|studionet|testnet_asimov|testnet_bradbury)$",
        help="One of: localnet | studionet | testnet_asimov | testnet_bradbury",
    ),
    EnvSpec(
        "GENLAYER_PRIVATE_KEY",
        required=True,
        secret=True,
        pattern=r"^0x[0-9a-fA-F]{64}$",
        help="Deployer private key (0x + 64 hex). Inject from CI secrets ONLY.",
    ),
    EnvSpec(
        "GENLAYER_CONTRACT_PATH",
        required=False,
        pattern=r".+\.py$",
        help="Path to the contract to deploy (overrides the resolved contract).",
    ),
)

# Chain-types for which an insecure (plain http, loopback) RPC is acceptable.
LOCAL_CHAINS = frozenset({"localnet"})


def mask(value: str) -> str:
    """Return a log-safe rendering of a possibly-sensitive value."""
    if not value:
        return "<empty>"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}…{value[-2:]} (len={len(value)})"


def require(condition: bool, message: str) -> None:
    """Assert a guardrail; raise GuardrailError (never AssertionError)."""
    if not condition:
        raise GuardrailError(message)


def resolve_env(specs: Iterable[EnvSpec]) -> dict[str, str]:
    """Validate and return the requested env vars.

    Raises GuardrailError listing *all* problems at once (so an operator fixes
    the environment in one pass instead of whack-a-mole).
    """
    resolved: dict[str, str] = {}
    problems: list[str] = []

    for spec in specs:
        raw = os.environ.get(spec.name, "").strip()
        if not raw:
            if spec.required:
                problems.append(f"  - {spec.name} is unset. {spec.help}")
            continue
        if spec.pattern and not re.search(spec.pattern, raw):
            shown = mask(raw) if spec.secret else raw
            problems.append(
                f"  - {spec.name}={shown} does not match required format. {spec.help}"
            )
            continue
        resolved[spec.name] = raw

    if problems:
        raise GuardrailError(
            "Environment guardrail failed:\n" + "\n".join(problems)
        )
    return resolved


# --------------------------------------------------------------------------- #
# RPC security                                                                #
# --------------------------------------------------------------------------- #


def validate_rpc(rpc_url: str, chain_type: str) -> str:
    """Enforce transport security rules for the RPC endpoint.

    Rules:
      * Any remote (non-local) chain MUST use https.
      * Plain http is only tolerated when pointing at loopback on localnet.
      * URL must be well-formed with an explicit scheme + host.
    Returns the validated url.
    """
    parsed = urlparse(rpc_url)
    require(
        parsed.scheme in ("http", "https") and bool(parsed.netloc),
        f"GENLAYER_RPC_URL is malformed: {rpc_url!r} (need scheme://host[:port]/path)",
    )

    host = (parsed.hostname or "").lower()
    is_loopback = host in ("127.0.0.1", "localhost", "0.0.0.0", "::1")

    if chain_type in LOCAL_CHAINS:
        # localnet may use http, but only against loopback — never a public host.
        require(
            parsed.scheme == "https" or is_loopback,
            f"localnet RPC over plain http is only allowed on loopback, got host={host!r}",
        )
    else:
        require(
            parsed.scheme == "https",
            f"chain_type={chain_type!r} requires an https RPC endpoint; refusing "
            f"to send a signed transaction over {parsed.scheme}.",
        )
        require(
            not is_loopback,
            f"chain_type={chain_type!r} points at loopback host {host!r}; that is "
            "almost certainly a mis-set GENLAYER_RPC_URL.",
        )
    return rpc_url


# --------------------------------------------------------------------------- #
# Consolidated pre-deploy gate                                                #
# --------------------------------------------------------------------------- #


@dataclass
class DeployContext:
    rpc_url: str
    chain_type: str
    private_key: str = field(repr=False)  # never rendered in tracebacks/logs
    contract_path: str = ""

    def redacted(self) -> dict[str, str]:
        return {
            "rpc_url": self.rpc_url,
            "chain_type": self.chain_type,
            "private_key": mask(self.private_key),
            "contract_path": self.contract_path,
        }


def build_deploy_context(contract_path: str) -> DeployContext:
    """Resolve + validate everything needed for a remote deploy.

    `contract_path` is the caller-resolved contract (no hardcoded default);
    the GENLAYER_CONTRACT_PATH env var, if set, overrides it.
    Raises GuardrailError on any missing/insecure configuration.
    """
    env = resolve_env(DEPLOY_ENV)
    chain_type = env["GENLAYER_CHAIN_TYPE"]
    rpc_url = validate_rpc(env["GENLAYER_RPC_URL"], chain_type)
    resolved = env.get("GENLAYER_CONTRACT_PATH") or contract_path
    require(bool(resolved), "no contract resolved for deploy (pass one explicitly).")
    return DeployContext(
        rpc_url=rpc_url,
        chain_type=chain_type,
        private_key=env["GENLAYER_PRIVATE_KEY"],
        contract_path=resolved,
    )
