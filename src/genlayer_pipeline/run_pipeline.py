#!/usr/bin/env python3
"""
run_pipeline.py — target-agnostic GenLayer CI/CD orchestration harness.

Single entry point that drives the four strict pipeline stages, in order:

    1. lint     -> genvm-lint AST safety + SDK semantic validation
    2. test     -> gltest direct-mode + (optional) multi-agent validation suites
    3. build    -> contract ABI schema extraction + frontend build validation
    4. deploy   -> deploy the contract to Studionet (guardrailed)

The harness has NO hardcoded project/contract references: what to run is
resolved dynamically from CLI args, an optional pipeline.toml, or auto-discovery
of the contracts directory (see pipeline_config.py). Point --root at any GenLayer
project.

Guarantees (per the design brief):
  * ZERO SILENT FAILURES. Every subprocess is timed, captured, and its exit code
    checked. A non-zero exit aborts the pipeline with a structured error.
  * Reproducible logs. Each stage writes a captured stdout/stderr log plus a
    machine-readable run summary (JSON) into the artifacts directory.
  * Fail-fast by default, with `--continue-on-error` for diagnostic full runs.
  * Secret-safe. RPC/private-key handling is delegated to guardrails.py, which
    never logs secret material.

Usage:
    genlayer-pipeline                       # lint -> test -> build
    genlayer-pipeline --stages all          # include deploy
    genlayer-pipeline --stages lint,test
    genlayer-pipeline --from build          # build -> deploy
    genlayer-pipeline --dry-run             # print plan, run nothing
    genlayer-pipeline --root /path/to/proj  # target any GenLayer project
    python -m genlayer_pipeline --json      # module form; NDJSON to stdout

Exit codes:
    0  all selected stages passed
    1  a stage failed (lint/test/build/deploy regression)
    2  guardrail / configuration error (fix the environment, then retry)
    3  usage / internal error
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Sibling modules in the installed package.
from genlayer_pipeline import guardrails as G
from genlayer_pipeline import deployment as D
from genlayer_pipeline import report as R
from genlayer_pipeline import pipeline_config as C

EXIT_OK = 0
EXIT_STAGE_FAILED = 1
EXIT_GUARDRAIL = 2
EXIT_USAGE = 3

def _ephemeral_password() -> str:
    """A strong throwaway password for the CI keystore (never persisted)."""
    import secrets
    return secrets.token_urlsafe(24)


def _as_text(data: str | bytes | None) -> str:
    """Coerce subprocess output (str/bytes/None) to text safely."""
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode("utf-8", "replace")
    return data


STAGE_ORDER = ["lint", "test", "build", "deploy"]
# Default run excludes deploy — deploying is an explicit, opt-in action.
DEFAULT_STAGES = ["lint", "test", "build"]


# --------------------------------------------------------------------------- #
# Project layout discovery                                                    #
# --------------------------------------------------------------------------- #


def find_project_root(start: Path) -> Path:
    """Walk upward from `start` until we find a dir containing both
    contracts/ and tests/ (a GenLayer project root). Falls back to `start`
    itself so behaviour is predictable when run standalone; pass an explicit
    --root to target an external project.
    """
    for candidate in [start, *start.parents]:
        if (candidate / "contracts").is_dir() and (candidate / "tests").is_dir():
            return candidate
    # Fallback: the starting directory (caller validates contracts/ exists).
    return start


# --------------------------------------------------------------------------- #
# Structured logging                                                          #
# --------------------------------------------------------------------------- #


class Logger:
    """Human-readable console output + a durable NDJSON event stream.

    Every event is appended to `ndjson_path` (for report.py's timeline) AND,
    in json_mode, echoed to stdout as NDJSON. Console mode prints a friendly
    line but still records the machine-readable event to the file.
    """

    def __init__(self, json_mode: bool, ndjson_path: Path | None = None) -> None:
        self.json_mode = json_mode
        self.ndjson_path = ndjson_path
        self._fh = None
        if ndjson_path is not None:
            ndjson_path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = ndjson_path.open("w")

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def _emit(self, level: str, event: str, **fields) -> None:
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
            **fields,
        }
        if self._fh is not None:
            self._fh.write(json.dumps(rec, default=str) + "\n")
            self._fh.flush()
        if self.json_mode:
            print(json.dumps(rec, default=str), flush=True)
        else:
            icon = {"INFO": "•", "OK": "✓", "FAIL": "✗", "WARN": "!"}.get(level, "·")
            detail = " ".join(f"{k}={v}" for k, v in fields.items() if k != "message")
            msg = fields.get("message", event)
            line = f"{icon} {msg}"
            if detail:
                line += f"   ({detail})"
            print(line, flush=True)

    def info(self, message: str, **f):
        self._emit("INFO", "info", message=message, **f)

    def ok(self, message: str, **f):
        self._emit("OK", "ok", message=message, **f)

    def warn(self, message: str, **f):
        self._emit("WARN", "warn", message=message, **f)

    def fail(self, message: str, **f):
        self._emit("FAIL", "fail", message=message, **f)


# --------------------------------------------------------------------------- #
# Stage result model                                                          #
# --------------------------------------------------------------------------- #


@dataclass
class StageResult:
    name: str
    status: str = "skipped"  # passed | failed | skipped
    exit_code: int | None = None
    duration_s: float = 0.0
    command: str = ""
    log_path: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "exit_code": self.exit_code,
            "duration_s": round(self.duration_s, 3),
            "command": self.command,
            "log_path": self.log_path,
            "error": self.error,
        }


# --------------------------------------------------------------------------- #
# Pipeline runner                                                             #
# --------------------------------------------------------------------------- #


@dataclass
class Runner:
    root: Path
    log: Logger
    artifacts_dir: Path
    contracts: list[str]          # resolved dynamically for lint + build
    deploy_contract: str | None   # single resolved contract for deploy
    contracts_dir: str
    tests_dir: str
    frontend_dir: str
    timeout_s: int
    continue_on_error: bool
    dry_run: bool
    mock_env: bool
    deploy_retries: int = 2
    deploy_backoff_s: float = 5.0
    verify_deploy: bool = True
    report_format: str = "text"
    ledger_path: Path | None = None
    on_failure: str | None = None  # command fired on any stage failure
    results: list[StageResult] = field(default_factory=list)

    # -- subprocess helper -------------------------------------------------- #
    def _run(self, name: str, cmd: list[str], *, env: dict | None = None,
             cwd: Path | None = None, redact: list[str] | None = None,
             failure_markers: list[str] | None = None,
             require_markers: list[str] | None = None) -> StageResult:
        """Run one subprocess with full capture + hard timeout. Never silent.

        stdin is always closed (DEVNULL): no stage may block on an interactive
        prompt (a real hazard with `genlayer deploy`'s keystore password prompt,
        which otherwise loops and exits 0 — a silent failure).

        Exit code 0 is necessary but NOT sufficient for success:
          * `failure_markers` — if any appears in output, force-fail even on exit 0.
          * `require_markers` — if none appears, force-fail even on exit 0.
        This closes the "tool printed an error but returned 0" hole.
        """
        display = " ".join(cmd)
        for secret in redact or []:
            if secret:
                display = display.replace(secret, "***")
        res = StageResult(name=name, command=display)
        log_file = self.artifacts_dir / f"{name}.log"
        res.log_path = str(log_file)

        if self.dry_run:
            self.log.info(f"[dry-run] {name}: {display}", cwd=str(cwd or self.root))
            res.status = "skipped"
            return res

        self.log.info(f"stage:{name} → {display}", cwd=str(cwd or self.root))
        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd or self.root),
                env={**os.environ, **(env or {})},
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                stdin=subprocess.DEVNULL,
            )
            res.exit_code = proc.returncode
            output = _as_text(proc.stdout) + _as_text(proc.stderr)
            log_file.write_text(output)

            hit = next((m for m in (failure_markers or []) if m in output), None)
            missing = (
                require_markers
                and not any(m in output for m in require_markers)
            )
            if proc.returncode == 0 and not hit and not missing:
                res.status = "passed"
            else:
                res.status = "failed"
                if hit:
                    res.error = f"failure marker in output: {hit!r}\n" + self._tail(output)
                elif missing:
                    res.error = (
                        f"none of the required success markers {require_markers} "
                        f"found (exit={proc.returncode})\n" + self._tail(output)
                    )
                    if res.exit_code == 0:
                        res.exit_code = 1  # normalise "false success" to a failure code
                else:
                    res.error = self._tail(output)
        except subprocess.TimeoutExpired as exc:
            res.status = "failed"
            res.exit_code = 124
            res.error = f"timed out after {self.timeout_s}s"
            log_file.write_text(_as_text(exc.stdout) + _as_text(exc.stderr))
        except FileNotFoundError as exc:
            res.status = "failed"
            res.exit_code = 127
            res.error = f"command not found: {exc.filename} — is the tool installed / venv active?"
        finally:
            res.duration_s = time.monotonic() - start

        if res.status == "passed":
            self.log.ok(f"stage:{name} passed", duration_s=round(res.duration_s, 2))
        else:
            self.log.fail(
                f"stage:{name} FAILED", exit_code=res.exit_code,
                duration_s=round(res.duration_s, 2), log=res.log_path,
            )
            if res.error:
                for line in res.error.splitlines():
                    self.log.fail(f"  {line}") if not self.log.json_mode else None
        return res

    def stage_deploy_plan(self) -> StageResult:
        """Dry-run placeholder for deploy: show intent without touching env/network."""
        res = StageResult(name="deploy", status="skipped")
        target = self.deploy_contract or "<resolved contract>"
        res.command = (
            f"genlayer deploy --contract <root>/{target} "
            "--rpc $GENLAYER_RPC_URL   (key via env)"
        )
        self.log.info(f"[dry-run] deploy: {res.command}")
        return res

    @staticmethod
    def _tail(text: str, n: int = 25) -> str:
        lines = [ln for ln in text.splitlines() if ln.strip()]
        return "\n".join(lines[-n:])

    def _no_contracts(self, stage: str) -> StageResult:
        """No contract could be resolved — fail loudly, don't silently pass."""
        res = StageResult(name=stage, status="failed", exit_code=1)
        res.error = (
            f"no contracts resolved for stage '{stage}'. Checked "
            f"'{self.contracts_dir}/*.py'. Pass --contract, set [project].contract "
            "in pipeline.toml, or point --root at a project with a contracts dir."
        )
        self.log.fail(f"stage:{stage} FAILED — {res.error}")
        return res

    def _run_per_contract(self, name, cmd_builder):
        """Run `cmd_builder(contract)` for each resolved contract, aggregating
        into ONE StageResult (fails if any contract fails). Keeps the per-stage
        model intact while supporting N contracts."""
        if self.dry_run:
            for c in self.contracts:
                self._run(name, cmd_builder(c))  # each prints its dry-run plan
            return StageResult(name=name, status="skipped")

        sub: list[StageResult] = []
        for c in self.contracts:
            r = self._run(f"{name}:{Path(c).stem}", cmd_builder(c))
            sub.append(r)
        # aggregate
        agg = StageResult(name=name)
        agg.command = f"{name} × {len(self.contracts)} contract(s)"
        agg.duration_s = sum(r.duration_s for r in sub)
        failed = [r for r in sub if r.status == "failed"]
        agg.status = "failed" if failed else "passed"
        agg.exit_code = failed[0].exit_code if failed else 0
        # aggregated log points at the per-contract logs
        agg.log_path = str(self.artifacts_dir / f"{name}.log")
        Path(agg.log_path).write_text(
            "\n".join(f"[{r.status}] {r.command}\n  log: {r.log_path}" for r in sub))
        if failed:
            agg.error = "; ".join(f"{r.name}: {r.error.splitlines()[0] if r.error else 'failed'}"
                                  for r in failed)
        return agg

    # -- stage: lint -------------------------------------------------------- #
    def stage_lint(self) -> StageResult:
        # `check` = fast AST lint + SDK semantic validate (the default workflow).
        # Runs over every resolved contract; the stage fails if any contract does.
        if not self.contracts:
            return self._no_contracts("lint")
        return self._run_per_contract(
            "lint",
            lambda c: ["genvm-lint", "check", str(self.root / c)],
        )

    # -- stage: test -------------------------------------------------------- #
    def stage_test(self) -> StageResult:
        # Direct-mode suite: deterministic, needs no running node (mock_llm).
        # Mock env isolates the run from any developer-local RPC/keys so a stray
        # env var can never silently redirect a "test" run at a live network.
        env = {}
        if self.mock_env:
            env = {
                "GENLAYER_RPC_URL": "http://127.0.0.1:4000/api",
                "GENLAYER_CHAIN_TYPE": "localnet",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            # Never let a real signer key leak into a test process.
            env["GENLAYER_PRIVATE_KEY"] = ""
        cmd = [
            "gltest", self.tests_dir,
            "-q",
            "--contracts-dir", self.contracts_dir,
            "--artifacts-dir", str(self.artifacts_dir / "gltest"),
            f"--junit-xml={self.artifacts_dir / 'junit-direct.xml'}",
        ]
        return self._run("test", cmd, env=env)

    # -- stage: build ------------------------------------------------------- #
    def stage_build(self) -> StageResult:
        # Build validation #1: ABI schema must extract cleanly for every contract
        # (compiles under the GenVM toolchain). This is the deploy-readiness gate.
        if not self.contracts:
            return self._no_contracts("build")
        res = self._run_per_contract(
            "build",
            lambda c: ["genvm-lint", "schema", str(self.root / c)],
        )
        if res.status == "passed" and not self.dry_run:
            # persist the aggregated schema output as an artifact
            try:
                (self.artifacts_dir / "abi_schema.json").write_text(
                    Path(res.log_path).read_text())
            except OSError:
                pass

        # Build validation #2 (optional): frontend production build, if present.
        fe = self.root / self.frontend_dir
        if res.status == "passed" and (fe / "package.json").exists():
            npm = shutil.which("npm")
            if npm is None:
                self.log.warn("frontend present but npm not found — skipping FE build")
            else:
                fe_res = self._run("build-frontend", [npm, "run", "build"], cwd=fe)
                if fe_res.status == "failed":
                    self.results.append(fe_res)
                    return fe_res
                self.results.append(fe_res)
        return res

    # -- stage: deploy ------------------------------------------------------ #
    def stage_deploy(self) -> StageResult:
        if self.dry_run:
            return self.stage_deploy_plan()
        # Guardrail gate BEFORE we touch the network. A GuardrailError here is a
        # configuration failure (exit 2), not a stage failure.
        if not self.deploy_contract:
            n = len(self.contracts)
            raise G.GuardrailError(
                "deploy target is ambiguous: "
                + (f"{n} contracts were discovered {self.contracts}; "
                   if n else "no contract could be resolved; ")
                + "specify one with --contract or [project].contract in pipeline.toml."
            )
        ctx = G.build_deploy_context(contract_path=self.deploy_contract)
        self.log.info("deploy target validated", **ctx.redacted())

        genlayer = shutil.which("genlayer")
        if genlayer is None:
            raise G.GuardrailError(
                "genlayer CLI not found on PATH — cannot deploy. "
                "Install with: npm i -g genlayer"
            )

        # `genlayer deploy` signs from an encrypted keystore, not from the raw
        # private-key env var, and it prompts interactively for a password. For
        # headless CI we import the key into an ephemeral keystore with a
        # generated password, then deploy with stdin closed so a mis-auth can
        # never hang or silently loop.
        password = os.environ.get("GENLAYER_KEYSTORE_PASSWORD") or _ephemeral_password()
        acct = "ci-deployer"

        import_res = self._run(
            "deploy-import",
            [genlayer, "account", "import",
             "--name", acct,
             "--private-key", ctx.private_key,
             "--password", password,
             "--overwrite"],
            redact=[ctx.private_key, password],
            failure_markers=["Invalid private key", "invalid length"],
        )
        if import_res.status == "failed":
            self.results.append(import_res)
            return import_res

        unlock_res = self._run(
            "deploy-unlock",
            [genlayer, "account", "unlock", "--account", acct, "--password", password],
            redact=[password],
        )
        # unlock is best-effort (some backends deploy fine without it); record it.
        self.results.append(unlock_res)

        cmd = [
            genlayer, "deploy",
            "--contract", str(self.root / ctx.contract_path),
            "--rpc", ctx.rpc_url,
        ]

        ledger = D.DeploymentLedger(self._ledger_path())
        previous = ledger.current_address or "(none)"
        sha = D.git_sha(self.root)

        # --- Recovery: retry the broadcast with backoff -------------------- #
        deploy_res = None
        for attempt in range(1, self.deploy_retries + 2):  # 1 try + N retries
            deploy_res = self._run(
                "deploy", cmd,
                env={"GENLAYER_KEYSTORE_PASSWORD": password},
                redact=[password, ctx.private_key],
                failure_markers=[
                    "Invalid password", "insufficient funds", "Deployment failed",
                    "ECONNREFUSED", "denied", "Attempt 2/3", "getaddrinfo",
                ],
                require_markers=["deployed successfully"],
            )
            if deploy_res.status == "passed":
                break
            if attempt <= self.deploy_retries:
                wait = self.deploy_backoff_s * attempt
                self.log.warn(f"deploy attempt {attempt} failed; retrying in {wait:.0f}s",
                              attempts_left=self.deploy_retries - attempt + 1)
                time.sleep(wait)

        assert deploy_res is not None

        # --- Rollback trigger #1: broadcast failed after all retries ------- #
        if deploy_res.status == "failed":
            rec = D.DeploymentRecord(
                address="", chain_type=ctx.chain_type, rpc_url=ctx.rpc_url,
                contract_path=ctx.contract_path, git_sha=sha,
            )
            decision = ledger.record_failure(rec, reason="broadcast failed after retries")
            self._log_rollback(decision)
            deploy_res.error = (f"deploy failed after {self.deploy_retries + 1} attempts; "
                                f"rolled back — clients keep {decision.kept_address or '(none)'}"
                                + ("\n" + deploy_res.error if deploy_res.error else ""))
            return deploy_res

        # --- Post-deploy verification (smoke test) ------------------------- #
        parsed = D.parse_deployment(_as_text(Path(deploy_res.log_path).read_text()))
        new_addr = parsed["address"]
        self.log.info("deploy broadcast ok", address=new_addr or "(unparsed)",
                      tx=parsed["tx_hash"] or "-")

        verify_ok = True
        if self.verify_deploy and new_addr:
            verify_res = self._run(
                "deploy-verify",
                [genlayer, "schema", new_addr, "--rpc", ctx.rpc_url],
                failure_markers=["Error", "not found", "does not exist", "ECONNREFUSED"],
                require_markers=["methods", "ctor", "{"],
            )
            self.results.append(verify_res)
            verify_ok = verify_res.status == "passed"
        elif self.verify_deploy and not new_addr:
            self.log.warn("could not parse deployed address; skipping smoke verify")

        # --- Rollback trigger #2: deployed but verification failed --------- #
        if not verify_ok:
            rec = D.DeploymentRecord(
                address=new_addr, tx_hash=parsed["tx_hash"], chain_type=ctx.chain_type,
                rpc_url=ctx.rpc_url, contract_path=ctx.contract_path, git_sha=sha,
            )
            decision = ledger.record_failure(rec, reason="post-deploy verification failed")
            self._log_rollback(decision)
            deploy_res.status = "failed"
            deploy_res.exit_code = 1
            deploy_res.error = (f"deployed {new_addr} but smoke verification failed; "
                                f"rolled back — clients keep {decision.kept_address or '(none)'}")
            self.log.fail(f"stage:deploy FAILED (post-deploy verify) — {deploy_res.error}")
            return deploy_res

        # --- Promote: verified good becomes the new current pointer -------- #
        rec = D.DeploymentRecord(
            address=new_addr, tx_hash=parsed["tx_hash"], chain_type=ctx.chain_type,
            rpc_url=ctx.rpc_url, contract_path=ctx.contract_path, git_sha=sha,
        )
        ledger.promote(rec)
        self.log.ok(f"deploy promoted → current live address {new_addr or '(unparsed)'}",
                    previous=previous, git_sha=sha)
        return deploy_res

    # -- deploy helpers ----------------------------------------------------- #
    def _ledger_path(self) -> Path:
        if self.ledger_path is not None:
            return self.ledger_path
        return self.artifacts_dir / "deployments" / "ledger.json"

    def _log_rollback(self, decision: "D.RollbackDecision") -> None:
        self.log.warn(
            "⟲ ROLLBACK triggered", reason=decision.reason,
            failed=decision.failed_address or "-",
            kept_live=decision.kept_address or "(none)",
        )
        if not decision.kept_address:
            self.log.warn("no previous good deployment exists — nothing live to fall back to; "
                          "downstream clients must not be re-pointed.")

    # -- driver ------------------------------------------------------------- #
    def run(self, stages: list[str]) -> int:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        (self.artifacts_dir / "gltest").mkdir(exist_ok=True)
        self.log.info("pipeline start", root=str(self.root), stages=",".join(stages),
                      artifacts=str(self.artifacts_dir))

        dispatch = {
            "lint": self.stage_lint,
            "test": self.stage_test,
            "build": self.stage_build,
            "deploy": self.stage_deploy,
        }

        overall = EXIT_OK
        for name in stages:
            try:
                result = dispatch[name]()
            except G.GuardrailError as exc:
                self.log.fail(f"stage:{name} guardrail refused to run")
                for line in str(exc).splitlines():
                    self.log.fail(f"  {line}")
                gr = StageResult(name=name, status="failed", exit_code=EXIT_GUARDRAIL,
                                 error=str(exc))
                self.results.append(gr)
                self._fire_failure_trigger(gr)
                self._write_summary(stages)
                self._aggregate_logs()
                self._append_history(EXIT_GUARDRAIL)
                self._emit_analytics()
                return EXIT_GUARDRAIL

            self.results.append(result)
            if result.status == "failed":
                overall = EXIT_STAGE_FAILED
                self._fire_failure_trigger(result)
                if not self.continue_on_error:
                    self.log.fail("aborting pipeline (fail-fast). "
                                  "Use --continue-on-error for a full diagnostic run.")
                    break

        self._write_summary(stages)
        self._print_report()
        self._aggregate_logs()
        self._append_history(overall)
        self._emit_analytics()
        return overall

    # -- Step 2: log aggregation, run history, failure triggers ------------- #
    def _aggregate_logs(self) -> None:
        """Concatenate every per-stage log into one consolidated aggregate.log
        with clear section headers — a single artifact to grep / attach / ship."""
        try:
            parts = []
            for logf in sorted(self.artifacts_dir.glob("*.log")):
                if logf.name == "aggregate.log":
                    continue
                parts.append("=" * 70)
                parts.append(f"===== {logf.stem} =====")
                parts.append("=" * 70)
                parts.append(logf.read_text().rstrip())
                parts.append("")
            (self.artifacts_dir / "aggregate.log").write_text("\n".join(parts))
        except OSError as exc:
            self.log.warn(f"log aggregation failed: {exc}")

    def _append_history(self, exit_code: int) -> None:
        """Append this run to history.ndjson for cross-run trend analytics."""
        try:
            rec = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "exit_code": exit_code,
                "passed": exit_code == EXIT_OK,
                "stages": {r.name: r.status for r in self.results},
                "durations": {r.name: round(r.duration_s, 3) for r in self.results},
                "git_sha": D.git_sha(self.root),
            }
            with (self.artifacts_dir / "history.ndjson").open("a") as fh:
                fh.write(json.dumps(rec) + "\n")
        except OSError as exc:
            self.log.warn(f"history append failed: {exc}")

    def _fire_failure_trigger(self, result: StageResult) -> None:
        """Error-handling trigger: on ANY stage failure, (1) write a structured
        alert artifact, and (2) if an on_failure hook is configured, invoke it
        with context via env. The trigger is best-effort and never masks or
        changes the original stage result."""
        alerts = self.artifacts_dir / "alerts"
        alert = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "stage": result.name,
            "exit_code": result.exit_code,
            "log": result.log_path,
            "error": (result.error or "").splitlines()[:20],
        }
        try:
            alerts.mkdir(parents=True, exist_ok=True)
            (alerts / f"{result.name.replace(':', '_')}.alert.json").write_text(
                json.dumps(alert, indent=2))
        except OSError as exc:
            self.log.warn(f"could not write alert artifact: {exc}")

        hook = self.on_failure or os.environ.get("PIPELINE_ON_FAILURE")
        if not hook or self.dry_run:
            return
        self.log.warn(f"firing on_failure trigger: {hook}", stage=result.name)
        try:
            hook_env = {
                **os.environ,
                "PIPELINE_FAILED_STAGE": result.name,
                "PIPELINE_EXIT_CODE": str(result.exit_code),
                "PIPELINE_LOG": result.log_path,
                "PIPELINE_ERROR": (result.error or "")[:2000],
            }
            proc = subprocess.run(hook, shell=True, cwd=str(self.root), env=hook_env,
                                  capture_output=True, text=True, timeout=120,
                                  stdin=subprocess.DEVNULL)
            (self.artifacts_dir / "alerts" / "on_failure.log").write_text(
                _as_text(proc.stdout) + _as_text(proc.stderr))
            if proc.returncode != 0:
                self.log.warn(f"on_failure trigger exited {proc.returncode} (non-fatal)")
        except (OSError, subprocess.SubprocessError) as exc:
            self.log.warn(f"on_failure trigger error (non-fatal): {exc}")

    def _emit_analytics(self) -> None:
        """Parse junit/summary/NDJSON into report.md + report.json, and echo."""
        try:
            self.log.close()  # flush events.ndjson so the timeline is complete
            rendered = R.generate(self.artifacts_dir, fmt=self.report_format, write=True)
        except Exception as exc:  # noqa: BLE001 — reporting must never mask results
            print(f"! analytics report generation failed: {exc}", file=sys.stderr)
            return
        if not self.log.json_mode:
            print("\n" + rendered)
            print(f"\n  Report:    {self.artifacts_dir / 'report.md'}")

    def _write_summary(self, requested: list[str]) -> None:
        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project_root": str(self.root),
            "requested_stages": requested,
            "results": [r.to_dict() for r in self.results],
            "passed": all(r.status != "failed" for r in self.results),
        }
        (self.artifacts_dir / "pipeline_summary.json").write_text(
            json.dumps(summary, indent=2)
        )

    def _print_report(self) -> None:
        if self.log.json_mode:
            return
        print("\n" + "─" * 60)
        print("Pipeline summary")
        print("─" * 60)
        for r in self.results:
            badge = {"passed": "PASS", "failed": "FAIL", "skipped": "SKIP"}[r.status]
            print(f"  [{badge}] {r.name:<16} {r.duration_s:6.2f}s   {r.command}")
        print("─" * 60)
        print(f"  Artifacts: {self.artifacts_dir}")
        print(f"  Summary:   {self.artifacts_dir / 'pipeline_summary.json'}")


# --------------------------------------------------------------------------- #
# CLI                                                                         #
# --------------------------------------------------------------------------- #


def parse_stages(args: argparse.Namespace) -> list[str]:
    if args.from_stage:
        if args.from_stage not in STAGE_ORDER:
            raise SystemExit(f"unknown --from stage: {args.from_stage}")
        idx = STAGE_ORDER.index(args.from_stage)
        return STAGE_ORDER[idx:]
    if not args.stages or args.stages == "default":
        return list(DEFAULT_STAGES)
    if args.stages == "all":
        return list(STAGE_ORDER)
    selected = [s.strip() for s in args.stages.split(",") if s.strip()]
    for s in selected:
        if s not in STAGE_ORDER:
            raise SystemExit(f"unknown stage {s!r}; valid: {', '.join(STAGE_ORDER)}")
    # keep canonical order
    return [s for s in STAGE_ORDER if s in selected]


def self_check(log: "Logger", root: Path, cfg: "C.PipelineConfig") -> int:
    """Clean-configuration check: assert the toolkit carries no hardcoded project
    references and print the dynamically resolved config. Returns 0 if generic.

    Scans the installed package's own source, so it works both in-repo and from
    site-packages.
    """
    import re
    log.info("── toolkit self-check ──")
    # 1. no hardcoded project/contract references in the shipped package source
    pkg_dir = Path(__file__).resolve().parent
    banned = re.compile(r"true[_-]?logix", re.IGNORECASE)
    offenders: list[str] = []
    for py in sorted(pkg_dir.glob("*.py")):
        for i, line in enumerate(py.read_text().splitlines(), 1):
            if banned.search(line):
                offenders.append(f"{py.name}:{i}: {line.strip()}")
    generic = not offenders
    if generic:
        log.ok(f"no hardcoded project references in {pkg_dir.name}/ (100% generic)")
    else:
        log.fail("hardcoded project references found:")
        for o in offenders:
            log.fail(f"  {o}")

    # 2. tool availability
    tools = {t: shutil.which(t) for t in ("genvm-lint", "gltest", "genlayer", "npm")}
    for t, path in tools.items():
        (log.ok if path else log.warn)(f"tool {t}: {path or 'NOT FOUND'}")

    # 3. resolved config against the current root
    log.info(f"resolved config for root={root}", **cfg.summary())
    if not cfg.contracts:
        log.warn("no contracts resolved at this root — pass --root at a GenLayer "
                 "project, or set [project].contract in pipeline.toml")

    log.ok("self-check PASSED" if generic else "self-check FAILED")
    return EXIT_OK if generic else EXIT_STAGE_FAILED


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Target-agnostic GenLayer CI/CD pipeline orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--stages", default="default",
                   help="'default' (lint,test,build), 'all', or comma list e.g. lint,test")
    p.add_argument("--from", dest="from_stage", default=None,
                   help="run this stage and everything after it (lint|test|build|deploy)")
    p.add_argument("--root", default=None, help="project root (auto-detected if omitted)")
    p.add_argument("--config", default=None,
                   help="path to pipeline.toml/json (else auto-found in root, then toolkit)")
    p.add_argument("--contract", default=None,
                   help="contract path(s) to lint/build/deploy (else config or auto-discover)")
    p.add_argument("--contracts-dir", default=None, help="contracts dir (default: contracts)")
    p.add_argument("--tests-dir", default=None, help="tests dir (default: tests/direct)")
    p.add_argument("--frontend-dir", default=None, help="frontend dir (default: frontend)")
    p.add_argument("--artifacts-dir", default=None,
                   help="where to write logs/summary (default: <root>/artifacts/pipeline)")
    p.add_argument("--timeout", type=int, default=900, help="per-stage timeout (s)")
    p.add_argument("--continue-on-error", action="store_true",
                   help="run all stages even after a failure (diagnostic mode)")
    p.add_argument("--no-mock-env", action="store_true",
                   help="do NOT inject the isolated mock env into the test stage")
    p.add_argument("--dry-run", action="store_true", help="print the plan; run nothing")
    p.add_argument("--json", action="store_true", help="emit NDJSON events to stdout")
    p.add_argument("--deploy-retries", type=int, default=None,
                   help="deploy broadcast retries before rollback (default: 2)")
    p.add_argument("--deploy-backoff", type=float, default=None,
                   help="base backoff seconds between deploy retries (linear) (default: 5)")
    p.add_argument("--no-verify-deploy", action="store_true",
                   help="skip the post-deploy smoke verification (not recommended)")
    p.add_argument("--report-format", choices=["text", "md", "json"], default="text",
                   help="analytics report rendered to console (report.md/json always written)")
    p.add_argument("--ledger-path", default=None,
                   help="deployment ledger path (default: <artifacts>/deployments/ledger.json; "
                        "also settable via PIPELINE_LEDGER_PATH)")
    p.add_argument("--self-check", action="store_true",
                   help="print resolved config + assert the toolkit is generic, then exit")
    args = p.parse_args(argv)

    log = Logger(json_mode=args.json)  # console-only until we know the artifacts dir
    # Fallback location for an auto-discovered pipeline.toml (the package dir).
    toolkit_root = Path(__file__).resolve().parent
    try:
        start = Path(args.root).resolve() if args.root else Path.cwd()
        root = start if (start / "contracts").is_dir() else find_project_root(start)

        cfg = C.build_config(
            root, toolkit_root,
            config_path=args.config,
            cli_contract=args.contract,
            cli_contracts_dir=args.contracts_dir,
            cli_tests_dir=args.tests_dir,
            cli_frontend_dir=args.frontend_dir,
            cli_deploy_retries=args.deploy_retries,
            cli_deploy_backoff=args.deploy_backoff,
            cli_verify_deploy=(False if args.no_verify_deploy else None),
        )

        if args.self_check:
            return self_check(log, root, cfg)

        if not (root / cfg.contracts_dir).is_dir():
            log.fail(f"could not locate a '{cfg.contracts_dir}/' dir under {root}; "
                     "pass --root or --contracts-dir")
            return EXIT_USAGE

        artifacts = (
            Path(args.artifacts_dir).resolve()
            if args.artifacts_dir
            else root / "artifacts" / "pipeline"
        )
        log = Logger(json_mode=args.json, ndjson_path=artifacts / "events.ndjson")
        log.info("config resolved", **cfg.summary())

        ledger_path = (
            Path(args.ledger_path).resolve() if args.ledger_path
            else Path(os.environ["PIPELINE_LEDGER_PATH"]).resolve()
            if os.environ.get("PIPELINE_LEDGER_PATH") else None
        )

        stages = parse_stages(args)
        runner = Runner(
            root=root,
            log=log,
            artifacts_dir=artifacts,
            contracts=cfg.contracts,
            deploy_contract=cfg.deploy_contract,
            contracts_dir=cfg.contracts_dir,
            tests_dir=cfg.tests_dir,
            frontend_dir=cfg.frontend_dir,
            timeout_s=args.timeout,
            continue_on_error=args.continue_on_error,
            dry_run=args.dry_run,
            mock_env=not args.no_mock_env,
            deploy_retries=cfg.deploy_retries,
            deploy_backoff_s=cfg.deploy_backoff,
            verify_deploy=cfg.verify_deploy,
            report_format=args.report_format,
            ledger_path=ledger_path,
            on_failure=cfg.on_failure,
        )
        return runner.run(stages)

    except C.ConfigError as exc:
        log.fail("config error")
        for line in str(exc).splitlines():
            log.fail(f"  {line}")
        return EXIT_GUARDRAIL
    except G.GuardrailError as exc:
        log.fail("guardrail error")
        for line in str(exc).splitlines():
            log.fail(f"  {line}")
        return EXIT_GUARDRAIL
    except KeyboardInterrupt:
        log.fail("interrupted")
        return EXIT_USAGE
    except Exception as exc:  # noqa: BLE001 — top-level: never crash silently
        log.fail(f"internal error: {type(exc).__name__}: {exc}")
        return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
