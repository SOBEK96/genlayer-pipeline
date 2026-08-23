"""
Deployment ledger, failure-recovery, and rollback for Studionet deploys.

GenLayer intelligent contracts are immutable once deployed — you cannot "undo" a
transaction on-chain. So "rollback" here has a precise, honest meaning:

    The pipeline maintains a *current* pointer to the last-known-good deployed
    contract address. A deploy is only promoted to `current` after it both
    (a) broadcasts successfully AND (b) passes a post-deploy smoke verification.
    If either fails, `current` is NOT advanced — clients keep talking to the
    previous good address. That reference-level rollback is the safe, real-world
    analogue of a rollback for immutable contracts.

This module provides:
  * `DeploymentLedger` — durable JSON record of current + history.
  * `parse_deployment` — extract the deployed address / tx from CLI output.
  * `RollbackDecision` — the outcome the runner acts on and logs.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_sha(root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(root), capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


# --------------------------------------------------------------------------- #
# Output parsing                                                             #
# --------------------------------------------------------------------------- #

_ADDR_RE = re.compile(r"contract_address:\s*'?(0x[0-9a-fA-F]{40})'?")
_TXHASH_RE = re.compile(r"(?:transaction_hash|tx_hash|txId|hash):\s*'?(0x[0-9a-fA-F]{64})'?")
_ANY_ADDR_RE = re.compile(r"0x[0-9a-fA-F]{40}")


def parse_deployment(output: str) -> dict[str, str]:
    """Best-effort extraction of the deployed contract address + tx hash."""
    addr_match = _ADDR_RE.search(output)
    address = addr_match.group(1) if addr_match else ""
    if not address:
        # fall back to the last 40-hex address printed (deploy prints it last)
        candidates = _ANY_ADDR_RE.findall(output)
        address = candidates[-1] if candidates else ""
    tx_match = _TXHASH_RE.search(output)
    return {"address": address, "tx_hash": tx_match.group(1) if tx_match else ""}


# --------------------------------------------------------------------------- #
# Ledger model                                                                #
# --------------------------------------------------------------------------- #


@dataclass
class DeploymentRecord:
    address: str
    chain_type: str
    rpc_url: str
    contract_path: str
    git_sha: str
    tx_hash: str = ""
    status: str = "active"          # active | failed | rolled_back
    reason: str = ""                # populated for failed / rolled_back
    deployed_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RollbackDecision:
    triggered: bool
    reason: str
    kept_address: str = ""          # the address clients keep using (previous good)
    failed_address: str = ""        # the deploy that was rejected (if any)


class DeploymentLedger:
    """Durable JSON ledger: { current: <record|null>, history: [<record>...] }.

    Location defaults under the artifacts dir; override with PIPELINE_LEDGER_PATH.
    In CI (ephemeral runners) persist this file as a build artifact or in a
    state branch so `current` survives across runs.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.current: DeploymentRecord | None = None
        self.history: list[DeploymentRecord] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            return
        cur = data.get("current")
        self.current = DeploymentRecord(**cur) if cur else None
        self.history = [DeploymentRecord(**h) for h in data.get("history", [])]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": _now(),
            "current": self.current.to_dict() if self.current else None,
            "history": [h.to_dict() for h in self.history],
        }
        self.path.write_text(json.dumps(payload, indent=2))

    @property
    def current_address(self) -> str:
        return self.current.address if self.current else ""

    def last_good(self) -> DeploymentRecord | None:
        """Most recent record that was promoted to active."""
        for rec in reversed(self.history):
            if rec.status == "active":
                return rec
        return None

    # -- state transitions -------------------------------------------------- #

    def promote(self, record: DeploymentRecord) -> None:
        """A verified-good deploy becomes the new current pointer."""
        record.status = "active"
        self.history.append(record)
        self.current = record
        self.save()

    def record_failure(self, record: DeploymentRecord, reason: str) -> RollbackDecision:
        """A broadcast or verification failure. `current` is NOT advanced.

        Returns the rollback decision the runner should log/act on.
        """
        record.status = "failed"
        record.reason = reason
        self.history.append(record)

        previous = self.last_good()
        # Append an explicit rolled_back marker so the audit trail is unambiguous.
        marker = DeploymentRecord(
            address=previous.address if previous else "",
            chain_type=record.chain_type,
            rpc_url=record.rpc_url,
            contract_path=record.contract_path,
            git_sha=record.git_sha,
            status="rolled_back",
            reason=f"kept previous good after: {reason}",
        )
        self.history.append(marker)
        # current stays as-is (the previous good); persist the audit trail.
        self.current = previous
        self.save()
        return RollbackDecision(
            triggered=True,
            reason=reason,
            kept_address=previous.address if previous else "",
            failed_address=record.address,
        )
