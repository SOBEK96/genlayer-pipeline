"""
Regression tests: signer (deployer key) handling and secret hygiene.

Steward request coverage -- "test failure cases around signer handling".

The pipeline never runs a deploy without a well-formed signer key, and it must
never leak that key into logs, tracebacks, or the resolved command line. These
tests pin both the FAILURE paths (missing / malformed key is refused loudly) and
the SUCCESS path (a valid key resolves), plus the masking invariants that keep
secret material out of any human-visible output.
"""

from __future__ import annotations

import pytest

from genlayer_pipeline import guardrails as G

VALID_KEY = "0x" + "a1" * 32          # 0x + 64 hex chars
VALID_RPC = "https://studio.genlayer.com/api"
VALID_CHAIN = "studionet"


def _set_signer_env(monkeypatch, *, key=VALID_KEY, rpc=VALID_RPC, chain=VALID_CHAIN):
    monkeypatch.setenv("GENLAYER_RPC_URL", rpc)
    monkeypatch.setenv("GENLAYER_CHAIN_TYPE", chain)
    monkeypatch.setenv("GENLAYER_PRIVATE_KEY", key)


# --------------------------------------------------------------------------- #
# Failure cases                                                               #
# --------------------------------------------------------------------------- #

def test_missing_signer_key_is_refused(clean_env):
    _set_signer_env(clean_env)
    clean_env.delenv("GENLAYER_PRIVATE_KEY", raising=False)
    with pytest.raises(G.GuardrailError) as exc:
        G.build_deploy_context(contract_path="contracts/c.py")
    assert "GENLAYER_PRIVATE_KEY" in str(exc.value)


def test_empty_signer_key_is_refused(clean_env):
    _set_signer_env(clean_env, key="   ")   # whitespace-only -> stripped to empty
    with pytest.raises(G.GuardrailError) as exc:
        G.build_deploy_context(contract_path="contracts/c.py")
    assert "GENLAYER_PRIVATE_KEY" in str(exc.value)


@pytest.mark.parametrize(
    "bad_key",
    [
        "0x" + "a" * 63,            # one hex short
        "0x" + "a" * 65,            # one hex long
        "a1" * 32,                  # missing 0x prefix
        "0x" + "zz" * 32,           # non-hex characters
        "0X" + "a" * 64,            # wrong-case prefix (pattern demands lowercase 0x)
        "0x" + "a" * 64 + "b",      # trailing junk
    ],
)
def test_malformed_signer_key_is_refused(clean_env, bad_key):
    _set_signer_env(clean_env, key=bad_key)
    with pytest.raises(G.GuardrailError) as exc:
        G.build_deploy_context(contract_path="contracts/c.py")
    assert "GENLAYER_PRIVATE_KEY" in str(exc.value)


def test_malformed_key_error_does_not_leak_the_secret(clean_env):
    """A rejected key must be masked in the error, never printed in full."""
    secret = "0x" + "de" * 31 + "beef"   # 66 chars -> fails the 64-hex pattern
    _set_signer_env(clean_env, key=secret)
    with pytest.raises(G.GuardrailError) as exc:
        G.build_deploy_context(contract_path="contracts/c.py")
    assert secret not in str(exc.value)


def test_all_missing_signer_problems_reported_together(clean_env):
    """resolve_env batches every problem so an operator fixes them in one pass."""
    # `clean_env` guarantees nothing GENLAYER_* is set going in.
    assert clean_env is not None
    with pytest.raises(G.GuardrailError) as exc:
        G.resolve_env(G.DEPLOY_ENV)
    message = str(exc.value)
    assert "GENLAYER_RPC_URL" in message
    assert "GENLAYER_CHAIN_TYPE" in message
    assert "GENLAYER_PRIVATE_KEY" in message


# --------------------------------------------------------------------------- #
# Success case                                                                #
# --------------------------------------------------------------------------- #

def test_valid_signer_resolves_context(clean_env):
    _set_signer_env(clean_env)
    ctx = G.build_deploy_context(contract_path="contracts/c.py")
    assert ctx.private_key == VALID_KEY
    assert ctx.chain_type == VALID_CHAIN
    assert ctx.rpc_url == VALID_RPC
    assert ctx.contract_path == "contracts/c.py"


def test_contract_path_env_overrides_caller(clean_env):
    _set_signer_env(clean_env)
    clean_env.setenv("GENLAYER_CONTRACT_PATH", "contracts/override.py")
    ctx = G.build_deploy_context(contract_path="contracts/caller.py")
    assert ctx.contract_path == "contracts/override.py"


# --------------------------------------------------------------------------- #
# Secret hygiene: masking + redaction never expose key material                #
# --------------------------------------------------------------------------- #

def test_mask_hides_middle_of_secret():
    masked = G.mask(VALID_KEY)
    assert VALID_KEY not in masked
    assert masked.startswith("0x")          # only the first 4 chars survive
    assert masked.endswith(str(len(VALID_KEY)) + ")")


@pytest.mark.parametrize("value,expected", [("", "<empty>"), ("short", "***")])
def test_mask_edge_cases(value, expected):
    assert G.mask(value) == expected


def test_deploy_context_redacted_masks_key(clean_env):
    _set_signer_env(clean_env)
    ctx = G.build_deploy_context(contract_path="contracts/c.py")
    red = ctx.redacted()
    assert red["private_key"] != VALID_KEY
    assert VALID_KEY not in str(red)
    # non-secret fields are shown verbatim
    assert red["rpc_url"] == VALID_RPC
    assert red["chain_type"] == VALID_CHAIN


def test_deploy_context_repr_does_not_render_key(clean_env):
    """The dataclass marks private_key repr=False; str(ctx) must not contain it."""
    _set_signer_env(clean_env)
    ctx = G.build_deploy_context(contract_path="contracts/c.py")
    assert VALID_KEY not in repr(ctx)
