"""
Self-tests for the Pipeline toolkit itself (run with `pytest selftests/` or
`make selftest`). These are the toolkit's own regression net — distinct from the
GenLayer *contract* tests the pipeline runs against a target project.

The first test permanently enforces the zero-trace audit: it fails CI if any
project-specific reference ever creeps back into the toolkit.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# Import from the package whether or not it is pip-installed (add src/ as a fallback).
sys.path.insert(0, str(ROOT / "src"))

from genlayer_pipeline import deployment as D          # noqa: E402
from genlayer_pipeline import guardrails as G          # noqa: E402
from genlayer_pipeline import pipeline_config as C     # noqa: E402

BANNED = re.compile(r"true[_-]?logix", re.IGNORECASE)


# --------------------------------------------------------------------------- #
# 1. Zero-trace regression guard                                              #
# --------------------------------------------------------------------------- #

_SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "dist", "build", ".pytest_cache"}


def _auditable_files() -> list[Path]:
    files = []
    for p in ROOT.rglob("*"):
        if _SKIP_DIRS & set(p.parts) or any(part.endswith(".egg-info") for part in p.parts):
            continue
        if p.is_file() and p.suffix in {".py", ".toml", ".yaml", ".yml", ".md",
                                        ".txt", ".json", ".example", ".sh", ".cfg",
                                        ".ini", ""} \
                or p.name in {"Makefile"}:
            files.append(p)
    return files


def test_no_hardcoded_project_references():
    """No file in the toolkit may mention the old project (case-insensitive)."""
    offenders = []
    for f in _auditable_files():
        try:
            for i, line in enumerate(f.read_text().splitlines(), 1):
                if BANNED.search(line):
                    offenders.append(f"{f.relative_to(ROOT)}:{i}: {line.strip()}")
        except (UnicodeDecodeError, OSError):
            continue
    assert not offenders, "hardcoded project references found:\n" + "\n".join(offenders)


# --------------------------------------------------------------------------- #
# 2. Dynamic contract resolution                                             #
# --------------------------------------------------------------------------- #

def _make_project(tmp: Path, contracts: list[str]) -> Path:
    (tmp / "contracts").mkdir(parents=True)
    (tmp / "tests" / "direct").mkdir(parents=True)
    for c in contracts:
        (tmp / "contracts" / c).write_text("from genlayer import *\n")
    return tmp


def test_autodiscovers_all_contracts(tmp_path):
    root = _make_project(tmp_path, ["alpha.py", "beta.py", "__init__.py", "test_x.py"])
    cfg = C.build_config(root, ROOT)
    # dunders and test_ files excluded; both real contracts discovered
    assert cfg.contracts == ["contracts/alpha.py", "contracts/beta.py"]
    # ambiguous -> no single deploy target
    assert cfg.deploy_contract is None


def test_single_contract_resolves_deploy(tmp_path):
    root = _make_project(tmp_path, ["only.py"])
    cfg = C.build_config(root, ROOT)
    assert cfg.deploy_contract == "contracts/only.py"


def test_config_file_overrides_defaults(tmp_path):
    root = _make_project(tmp_path, ["alpha.py", "beta.py"])
    (root / "pipeline.toml").write_text(
        '[project]\ncontract = "contracts/beta.py"\n[deploy]\nretries = 7\n')
    cfg = C.build_config(root, ROOT)
    assert cfg.contracts == ["contracts/beta.py"]
    assert cfg.deploy_contract == "contracts/beta.py"
    assert cfg.deploy_retries == 7
    assert cfg.source.endswith("pipeline.toml")


def test_cli_overrides_config_file(tmp_path):
    root = _make_project(tmp_path, ["alpha.py"])
    (root / "pipeline.toml").write_text('[project]\ncontract = "contracts/alpha.py"\n')
    cfg = C.build_config(root, ROOT, cli_contract="contracts/override.py")
    assert cfg.deploy_contract == "contracts/override.py"


# --------------------------------------------------------------------------- #
# 3. Guardrails                                                               #
# --------------------------------------------------------------------------- #

def test_rpc_rejects_plaintext_on_remote_chain():
    with pytest.raises(G.GuardrailError):
        G.validate_rpc("http://insecure/api", "studionet")


def test_rpc_allows_https_on_remote_chain():
    assert G.validate_rpc("https://studio/api", "studionet").startswith("https")


def test_rpc_allows_loopback_http_on_localnet():
    assert G.validate_rpc("http://127.0.0.1:4000/api", "localnet")


# --------------------------------------------------------------------------- #
# 4. Deployment ledger + rollback                                            #
# --------------------------------------------------------------------------- #

def test_rollback_keeps_last_good(tmp_path):
    ledger = D.DeploymentLedger(tmp_path / "ledger.json")
    good = D.DeploymentRecord(address="0x" + "a" * 40, chain_type="studionet",
                              rpc_url="https://x/api", contract_path="c.py", git_sha="s")
    ledger.promote(good)
    decision = ledger.record_failure(
        D.DeploymentRecord(address="", chain_type="studionet", rpc_url="https://x/api",
                           contract_path="c.py", git_sha="s"),
        reason="broadcast failed")
    assert decision.triggered
    assert ledger.current_address == good.address       # pointer unchanged
    # persistence survives reload
    assert D.DeploymentLedger(tmp_path / "ledger.json").current_address == good.address


def test_parse_deployment_extracts_address():
    out = "…\n  contract_address: '0x" + "b" * 40 + "'\n"
    assert D.parse_deployment(out)["address"] == "0x" + "b" * 40
