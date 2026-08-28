"""
Regression tests: deployed-address and transaction-hash parsing.

Steward request coverage -- "test failure cases around address parsing".

`parse_deployment` scrapes the deploy CLI's free-text output for the deployed
contract address and tx hash. It must be strict about the shape of an address
(0x + exactly 40 hex), correct about which candidate to pick when several are
printed, and safe (empty, never a crash) when nothing matches.
"""

from __future__ import annotations

import pytest

from genlayer_pipeline import deployment as D

ADDR = "0x" + "b" * 40
TXH = "0x" + "c" * 64


# --------------------------------------------------------------------------- #
# Success paths                                                               #
# --------------------------------------------------------------------------- #

def test_parses_labelled_address_and_tx():
    out = (
        "deploying...\n"
        f"  contract_address: '{ADDR}'\n"
        f"  transaction_hash: '{TXH}'\n"
        "deployed successfully\n"
    )
    parsed = D.parse_deployment(out)
    assert parsed["address"] == ADDR
    assert parsed["tx_hash"] == TXH


def test_labelled_address_without_quotes():
    out = f"contract_address: {ADDR}\n"
    assert D.parse_deployment(out)["address"] == ADDR


@pytest.mark.parametrize("label", ["transaction_hash", "tx_hash", "txId", "hash"])
def test_recognises_each_tx_label(label):
    out = f"contract_address: '{ADDR}'\n{label}: '{TXH}'\n"
    assert D.parse_deployment(out)["tx_hash"] == TXH


def test_falls_back_to_last_bare_address():
    """With no explicit label, deploy prints the address last; take that one."""
    first = "0x" + "1" * 40
    last = "0x" + "2" * 40
    out = f"from {first} ...\n... resulting contract {last}\n"
    assert D.parse_deployment(out)["address"] == last


def test_labelled_address_wins_over_bare_addresses():
    bare = "0x" + "9" * 40
    out = f"deployer {bare}\ncontract_address: '{ADDR}'\ntrailing {bare}\n"
    assert D.parse_deployment(out)["address"] == ADDR


# --------------------------------------------------------------------------- #
# Failure / edge cases                                                        #
# --------------------------------------------------------------------------- #

def test_no_address_returns_empty_not_error():
    parsed = D.parse_deployment("nothing deployed here\n")
    assert parsed == {"address": "", "tx_hash": ""}


def test_empty_output_is_safe():
    assert D.parse_deployment("") == {"address": "", "tx_hash": ""}


def test_too_short_hex_is_not_an_address():
    short = "0x" + "a" * 39
    assert D.parse_deployment(f"value {short}\n")["address"] == ""


def test_over_long_hex_is_truncated_to_forty():
    """A 0x followed by >40 hex still yields a 40-hex match, never a partial miss."""
    over = "0x" + "a" * 50
    got = D.parse_deployment(f"weird {over}\n")["address"]
    assert got == "0x" + "a" * 40


def test_address_missing_tx_hash_still_parses_address():
    parsed = D.parse_deployment(f"contract_address: '{ADDR}'\n")
    assert parsed["address"] == ADDR
    assert parsed["tx_hash"] == ""


def test_mixed_case_hex_is_accepted():
    mixed = "0xAbCdEf0123456789aBcDeF0123456789AbCdEf01"
    assert D.parse_deployment(f"contract_address: '{mixed}'\n")["address"] == mixed
