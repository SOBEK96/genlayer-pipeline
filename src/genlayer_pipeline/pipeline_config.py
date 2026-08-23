"""
pipeline_config.py — target-agnostic configuration + contract discovery.

The toolkit ships with NO hardcoded project or contract references. What to run
is resolved dynamically, in this precedence order (highest first):

    1. CLI arguments        (--contract, --contracts-dir, --tests-dir, …)
    2. a config file        (pipeline.toml / pipeline.json in the target, then
                             in the toolkit root)
    3. convention defaults  (contracts/, tests/direct/, frontend/)
    4. auto-discovery       (every *.py in the contracts dir)

So the same harness runs against any GenLayer project by pointing `--root` at it
— optionally dropping a `pipeline.toml` in that project to override conventions.

Example `pipeline.toml`:

    [project]
    contracts_dir = "contracts"
    tests_dir     = "tests/direct"
    frontend_dir  = "frontend"
    # contract = "contracts/my_contract.py"   # or ["a.py", "b.py"]; omit to auto-discover

    [deploy]
    retries = 2
    backoff = 5.0
    verify  = true

    [triggers]
    on_failure = "scripts/notify.sh"          # optional; run on any stage failure
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_FILENAMES = ("pipeline.toml", "pipeline.json")

DEFAULTS = {
    "contracts_dir": "contracts",
    "tests_dir": "tests/direct",
    "frontend_dir": "frontend",
    "deploy_retries": 2,
    "deploy_backoff": 5.0,
    "verify_deploy": True,
    "on_failure": None,
}


class ConfigError(RuntimeError):
    """Raised when a config file exists but is unusable, or resolution is ambiguous."""


@dataclass
class PipelineConfig:
    contracts_dir: str
    tests_dir: str
    frontend_dir: str
    contracts: list[str]          # relative paths for lint + build (may be empty)
    deploy_contract: str | None   # single contract for deploy (None if ambiguous/none)
    deploy_retries: int
    deploy_backoff: float
    verify_deploy: bool
    on_failure: str | None
    source: str                   # human description of where config came from

    def summary(self) -> dict:
        return {
            "config_source": self.source,
            "contracts_dir": self.contracts_dir,
            "tests_dir": self.tests_dir,
            "frontend_dir": self.frontend_dir,
            "contracts": self.contracts,
            "deploy_contract": self.deploy_contract or "(unresolved)",
            "deploy_retries": self.deploy_retries,
            "deploy_backoff": self.deploy_backoff,
            "verify_deploy": self.verify_deploy,
            "on_failure": self.on_failure or "(none)",
        }


# --------------------------------------------------------------------------- #
# File loading                                                               #
# --------------------------------------------------------------------------- #


def _load_file(path: Path) -> dict:
    try:
        if path.suffix == ".toml":
            return tomllib.loads(path.read_text())
        return json.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"could not parse config {path}: {exc}") from exc


def _find_config(target_root: Path, toolkit_root: Path, explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = (target_root / p)
        if not p.exists():
            raise ConfigError(f"--config {explicit} not found")
        return p
    for base in (target_root, toolkit_root):
        for name in CONFIG_FILENAMES:
            cand = base / name
            if cand.exists():
                return cand
    return None


def _flatten(raw: dict) -> dict:
    """Flatten the [project]/[deploy]/[triggers] tables into a flat override dict."""
    out: dict = {}
    proj = raw.get("project", {})
    for k in ("contracts_dir", "tests_dir", "frontend_dir", "contract"):
        if k in proj:
            out[k] = proj[k]
    dep = raw.get("deploy", {})
    if "retries" in dep:
        out["deploy_retries"] = dep["retries"]
    if "backoff" in dep:
        out["deploy_backoff"] = dep["backoff"]
    if "verify" in dep:
        out["verify_deploy"] = dep["verify"]
    trig = raw.get("triggers", {})
    if "on_failure" in trig:
        out["on_failure"] = trig["on_failure"]
    return out


# --------------------------------------------------------------------------- #
# Contract discovery                                                          #
# --------------------------------------------------------------------------- #


def discover_contracts(target_root: Path, contracts_dir: str) -> list[str]:
    """Every *.py in the contracts dir that looks like a contract (not a test /
    dunder / package init). Returns paths relative to target_root, sorted.
    """
    cdir = target_root / contracts_dir
    if not cdir.is_dir():
        return []
    found = []
    for p in sorted(cdir.glob("*.py")):
        name = p.name
        if name.startswith("__") or name.startswith("test_") or name.endswith("_test.py"):
            continue
        found.append(str(p.relative_to(target_root)))
    return found


# --------------------------------------------------------------------------- #
# Resolution                                                                  #
# --------------------------------------------------------------------------- #


def build_config(
    target_root: Path,
    toolkit_root: Path,
    *,
    config_path: str | None = None,
    cli_contract: str | None = None,
    cli_contracts_dir: str | None = None,
    cli_tests_dir: str | None = None,
    cli_frontend_dir: str | None = None,
    cli_deploy_retries: int | None = None,
    cli_deploy_backoff: float | None = None,
    cli_verify_deploy: bool | None = None,
) -> PipelineConfig:
    cfg = dict(DEFAULTS)
    source = "defaults"

    found = _find_config(target_root, toolkit_root, config_path)
    if found is not None:
        cfg.update(_flatten(_load_file(found)))
        source = str(found)

    # CLI overrides (only when explicitly provided)
    if cli_contracts_dir is not None:
        cfg["contracts_dir"] = cli_contracts_dir
    if cli_tests_dir is not None:
        cfg["tests_dir"] = cli_tests_dir
    if cli_frontend_dir is not None:
        cfg["frontend_dir"] = cli_frontend_dir
    if cli_deploy_retries is not None:
        cfg["deploy_retries"] = cli_deploy_retries
    if cli_deploy_backoff is not None:
        cfg["deploy_backoff"] = cli_deploy_backoff
    if cli_verify_deploy is not None:
        cfg["verify_deploy"] = cli_verify_deploy

    contracts_dir = cfg["contracts_dir"]

    # Resolve the contract set for lint/build.
    explicit_contract = cli_contract or cfg.get("contract")
    if explicit_contract:
        contracts = [explicit_contract] if isinstance(explicit_contract, str) else list(explicit_contract)
    else:
        contracts = discover_contracts(target_root, contracts_dir)

    # Resolve the single deploy contract.
    if cli_contract:
        deploy_contract: str | None = cli_contract
    elif isinstance(cfg.get("contract"), str):
        deploy_contract = cfg["contract"]
    elif len(contracts) == 1:
        deploy_contract = contracts[0]
    else:
        deploy_contract = None  # ambiguous / none — deploy stage will refuse

    return PipelineConfig(
        contracts_dir=contracts_dir,
        tests_dir=cfg["tests_dir"],
        frontend_dir=cfg["frontend_dir"],
        contracts=contracts,
        deploy_contract=deploy_contract,
        deploy_retries=int(cfg["deploy_retries"]),
        deploy_backoff=float(cfg["deploy_backoff"]),
        verify_deploy=bool(cfg["verify_deploy"]),
        on_failure=cfg.get("on_failure"),
        source=source,
    )
