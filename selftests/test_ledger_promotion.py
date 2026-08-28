"""
Regression tests: deployment ledger promotion flows + accounting invariants.

Steward request coverage -- "test failure cases around ... ledger promotion".

The ledger holds a single `current` pointer (the last-known-good live address)
plus an append-only `history`. The core safety invariant for immutable contracts:

    `current` only advances on a verified-good deploy (promote). A broadcast or
    verification FAILURE never advances it -- clients keep talking to the previous
    good address, and an explicit `rolled_back` marker is appended for audit.

These tests pin the promotion flow, the reference-level rollback, the audit trail,
and durability across reload.
"""

from __future__ import annotations

from pathlib import Path

from genlayer_pipeline import deployment as D


def _record(addr: str, **over) -> D.DeploymentRecord:
    base = dict(
        address=addr,
        chain_type="studionet",
        rpc_url="https://studio.genlayer.com/api",
        contract_path="contracts/c.py",
        git_sha="abc1234",
    )
    base.update(over)
    return D.DeploymentRecord(**base)


A = "0x" + "a" * 40
B = "0x" + "b" * 40
C = "0x" + "c" * 40


# --------------------------------------------------------------------------- #
# Promotion (success) flow                                                    #
# --------------------------------------------------------------------------- #

def test_promote_sets_current_and_marks_active(tmp_path):
    ledger = D.DeploymentLedger(tmp_path / "ledger.json")
    assert ledger.current_address == ""          # empty ledger has no live address
    ledger.promote(_record(A))
    assert ledger.current_address == A
    assert ledger.current is not None
    assert ledger.current.status == "active"
    assert ledger.history[-1].status == "active"


def test_successive_promotions_advance_the_pointer(tmp_path):
    ledger = D.DeploymentLedger(tmp_path / "ledger.json")
    ledger.promote(_record(A))
    ledger.promote(_record(B))
    assert ledger.current_address == B
    # history keeps every promotion in order
    active = [h.address for h in ledger.history if h.status == "active"]
    assert active == [A, B]


def test_last_good_returns_most_recent_active(tmp_path):
    ledger = D.DeploymentLedger(tmp_path / "ledger.json")
    ledger.promote(_record(A))
    ledger.promote(_record(B))
    lg = ledger.last_good()
    assert lg is not None and lg.address == B


# --------------------------------------------------------------------------- #
# Failure flow: pointer must NOT advance                                      #
# --------------------------------------------------------------------------- #

def test_failure_keeps_previous_good_current(tmp_path):
    ledger = D.DeploymentLedger(tmp_path / "ledger.json")
    ledger.promote(_record(A))
    decision = ledger.record_failure(_record(B), reason="broadcast failed after retries")
    assert decision.triggered is True
    assert decision.kept_address == A
    assert decision.failed_address == B
    # the pointer is unchanged -- clients keep the previous good address
    assert ledger.current_address == A


def test_failure_appends_failed_and_rolled_back_markers(tmp_path):
    ledger = D.DeploymentLedger(tmp_path / "ledger.json")
    ledger.promote(_record(A))
    ledger.record_failure(_record(B), reason="post-deploy verification failed")
    statuses = [h.status for h in ledger.history]
    assert "failed" in statuses
    assert "rolled_back" in statuses
    # the failed record carries the reason; the marker references the kept address
    failed = next(h for h in ledger.history if h.status == "failed")
    rolled = next(h for h in ledger.history if h.status == "rolled_back")
    assert failed.address == B
    assert "post-deploy verification failed" in failed.reason
    assert rolled.address == A


def test_first_deploy_failure_with_no_prior_good(tmp_path):
    """No previous good exists -> nothing live to fall back to; current stays None."""
    ledger = D.DeploymentLedger(tmp_path / "ledger.json")
    decision = ledger.record_failure(_record(B), reason="broadcast failed")
    assert decision.triggered is True
    assert decision.kept_address == ""
    assert ledger.current is None
    assert ledger.current_address == ""


def test_failure_after_success_does_not_lose_earlier_good(tmp_path):
    ledger = D.DeploymentLedger(tmp_path / "ledger.json")
    ledger.promote(_record(A))
    ledger.promote(_record(B))
    ledger.record_failure(_record(C), reason="verification failed")
    # falls back to B (the most recent active), not A
    assert ledger.current_address == B


# --------------------------------------------------------------------------- #
# Durability / accounting invariants across reload                            #
# --------------------------------------------------------------------------- #

def test_ledger_survives_reload(tmp_path):
    path = tmp_path / "ledger.json"
    ledger = D.DeploymentLedger(path)
    ledger.promote(_record(A))
    ledger.record_failure(_record(B), reason="broadcast failed")

    reloaded = D.DeploymentLedger(path)
    assert reloaded.current_address == A
    assert [h.status for h in reloaded.history] == [h.status for h in ledger.history]


def test_history_is_append_only_and_grows(tmp_path):
    ledger = D.DeploymentLedger(tmp_path / "ledger.json")
    ledger.promote(_record(A))
    n_after_promote = len(ledger.history)
    ledger.record_failure(_record(B), reason="broadcast failed")
    # a failure appends exactly two rows (failed + rolled_back marker)
    assert len(ledger.history) == n_after_promote + 2


def test_corrupt_ledger_file_loads_as_empty(tmp_path):
    """A garbled ledger must not crash startup; it degrades to an empty ledger."""
    path = tmp_path / "ledger.json"
    path.write_text("{ this is not valid json ")
    ledger = D.DeploymentLedger(path)
    assert ledger.current is None
    assert ledger.history == []
    # and it can still promote cleanly over the top
    ledger.promote(_record(A))
    assert ledger.current_address == A


def test_saved_ledger_is_wellformed_json(tmp_path):
    import json

    path = tmp_path / "ledger.json"
    ledger = D.DeploymentLedger(path)
    ledger.promote(_record(A))
    data = json.loads(Path(path).read_text())
    assert data["current"]["address"] == A
    assert isinstance(data["history"], list)
    assert "updated_at" in data
