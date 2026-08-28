"""
Regression tests: verification logic and transport/cryptographic checks.

Steward request coverage -- "test failure cases around ... verification".

Two verification layers are pinned here:

  1. RPC transport verification (`guardrails.validate_rpc`): a signed transaction
     must never leave over plain http on a remote chain; loopback http is only
     tolerated on localnet; malformed URLs are rejected.

  2. Output-marker verification (`run_pipeline.Runner._run`): a zero exit code is
     necessary but NOT sufficient. `require_markers` force a failure when an
     expected success token is absent, and `failure_markers` force a failure when
     a known error token is present -- closing the "tool printed an error but
     returned 0" hole that the post-deploy smoke check relies on.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from genlayer_pipeline import guardrails as G
from genlayer_pipeline import run_pipeline as RP


# --------------------------------------------------------------------------- #
# 1. RPC transport verification                                              #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("chain", ["studionet", "testnet_asimov", "testnet_bradbury"])
def test_remote_chain_requires_https(chain):
    with pytest.raises(G.GuardrailError):
        G.validate_rpc("http://node.example.com/api", chain)


def test_remote_chain_rejects_loopback_even_over_https():
    with pytest.raises(G.GuardrailError):
        G.validate_rpc("https://127.0.0.1:4000/api", "studionet")


def test_remote_chain_accepts_https():
    assert G.validate_rpc("https://studio.genlayer.com/api", "studionet").startswith("https")


def test_localnet_allows_loopback_http():
    assert G.validate_rpc("http://127.0.0.1:4000/api", "localnet")


def test_localnet_rejects_public_http_host():
    with pytest.raises(G.GuardrailError):
        G.validate_rpc("http://public.example.com/api", "localnet")


@pytest.mark.parametrize(
    "bad_url",
    ["", "not-a-url", "ftp://host/api", "https://", "://host/api", "host:4000/api"],
)
def test_malformed_rpc_url_is_rejected(bad_url):
    with pytest.raises(G.GuardrailError):
        G.validate_rpc(bad_url, "studionet")


# --------------------------------------------------------------------------- #
# 2. Output-marker verification via the real subprocess runner                #
# --------------------------------------------------------------------------- #

def _make_runner(tmp_path: Path) -> RP.Runner:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    log = RP.Logger(json_mode=True, ndjson_path=artifacts / "events.ndjson")
    return RP.Runner(
        root=tmp_path,
        log=log,
        artifacts_dir=artifacts,
        contracts=[],
        deploy_contract=None,
        contracts_dir="contracts",
        tests_dir="tests/direct",
        frontend_dir="frontend",
        timeout_s=30,
        continue_on_error=False,
        dry_run=False,
        mock_env=True,
    )


def _echo(text: str) -> list[str]:
    """A portable command that prints `text` and exits 0."""
    return [sys.executable, "-c", f"print({text!r})"]


def test_success_marker_present_passes(tmp_path):
    runner = _make_runner(tmp_path)
    res = runner._run(
        "verify", _echo("contract deployed successfully at 0xabc"),
        require_markers=["deployed successfully"],
    )
    assert res.status == "passed"
    assert res.exit_code == 0


def test_missing_required_marker_forces_failure_on_exit_zero(tmp_path):
    runner = _make_runner(tmp_path)
    res = runner._run(
        "verify", _echo("all good, nothing to see"),
        require_markers=["deployed successfully"],
    )
    assert res.status == "failed"
    # a "false success" (exit 0 but no marker) is normalised to a failure code
    assert res.exit_code == 1
    assert "required success markers" in res.error


def test_failure_marker_present_forces_failure_on_exit_zero(tmp_path):
    runner = _make_runner(tmp_path)
    res = runner._run(
        "verify", _echo("Deployment failed: insufficient funds"),
        failure_markers=["Deployment failed", "insufficient funds"],
    )
    assert res.status == "failed"
    assert "failure marker" in res.error


def test_nonzero_exit_fails_and_tails_output(tmp_path):
    runner = _make_runner(tmp_path)
    res = runner._run("verify", [sys.executable, "-c", "import sys; print('boom'); sys.exit(3)"])
    assert res.status == "failed"
    assert res.exit_code == 3


def test_missing_command_is_reported_not_crashed(tmp_path):
    runner = _make_runner(tmp_path)
    res = runner._run("verify", ["definitely-not-a-real-binary-xyz"])
    assert res.status == "failed"
    assert res.exit_code == 127
    assert "command not found" in res.error


def test_secret_is_redacted_in_recorded_command(tmp_path):
    runner = _make_runner(tmp_path)
    secret = "0x" + "de" * 32
    res = runner._run("verify", _echo("ok " + secret), redact=[secret])
    assert secret not in res.command
    assert "***" in res.command
