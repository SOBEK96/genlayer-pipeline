# Pipeline — Target-Agnostic GenLayer CI/CD & Automated Testing Toolkit

> Enterprise-grade automation for **any** GenLayer intelligent-contract project:
> **Lint → Test → Build Validation → Studionet Deployment**.
> No hardcoded project/contract references — what to run is resolved dynamically
> from CLI args, an optional `pipeline.toml`, or auto-discovery.

This is a **standalone** automation toolkit (workspace root: `/Users/ehs4n/Pipeline`).
It runs the pipeline *against* a target GenLayer project — pass `TARGET=/path/to/project`
(default: the current directory) — and always writes artifacts back **into this
workspace**, so a run never leaves traces in the target repo. The same reproducible
harness runs both locally (`make ci`) and in GitHub Actions, so "works on my machine"
and "works in CI" are the same code path.

---

## 0. Configuration (fully decoupled)

Nothing about the target project is hardcoded. What to run is resolved with this
precedence (highest first):

1. **CLI args** — `--contract`, `--contracts-dir`, `--tests-dir`, `--config`, …
2. **`pipeline.toml`** — auto-found in the target root, then the toolkit root
   (see [`config/pipeline.example.toml`](config/pipeline.example.toml))
3. **convention defaults** — `contracts/`, `tests/direct/`, `frontend/`
4. **auto-discovery** — every `*.py` in the contracts dir (excluding tests/dunders)

`lint` and `build` run over **all** resolved contracts; `deploy` requires exactly
one (explicit, or a single discovered contract — otherwise it refuses as ambiguous).

```bash
make doctor                         # clean-config check: asserts 0 hardcoded refs
                                    # + prints the dynamically resolved config
genlayer-pipeline --root <proj> --self-check
```

Minimal `pipeline.toml` dropped in a target project:

```toml
[project]
contract = "contracts/my_contract.py"   # omit to auto-discover
[deploy]
retries = 3
[triggers]
on_failure = "scripts/notify.sh"        # runs on any stage failure (see §6.3)
```

---

## 1. Architecture blueprint

### 1.1 Stage graph

```
 ┌──────────┐   ┌──────────┐   ┌────────────────┐   ┌──────────────────┐
 │ 1. LINT  │──▶│ 2. TEST  │──▶│ 3. BUILD VALID │──▶│ 4. DEPLOY        │
 │ genvm-   │   │ gltest   │   │ ABI schema +   │   │ Studionet        │
 │ lint     │   │ direct/  │   │ frontend build │   │ (guardrailed)    │
 │ check    │   │ multi-ag │   │                │   │                  │
 └──────────┘   └──────────┘   └────────────────┘   └──────────────────┘
   fail-fast       fail-fast       fail-fast            opt-in + gated
      │                │                │                     │
      └────────────────┴────────────────┴─────────────────────┘
                      every stage writes captured logs +
                    JUnit XML + pipeline_summary.json to
                          <root>/artifacts/pipeline/
```

A downstream stage **cannot** start unless every upstream stage is green — in CI
via `needs:`, locally via fail-fast ordering in the runner.

### 1.2 What each stage does

| Stage | Tool | Command (via harness) | Gate |
|-------|------|-----------------------|------|
| **1 · Lint** | `genvm-lint check` | AST safety checks + SDK semantic validation of the contract | any violation → abort |
| **2 · Test** | `gltest` | direct-mode suite (`tests/direct`, `mock_llm`, no node) + multi-agent validator checks; emits JUnit XML | any failing test → abort |
| **3 · Build** | `genvm-lint schema` + `npm run build` | contract ABI must extract (deploy-readiness) + frontend production bundle compiles | schema/build error → abort |
| **4 · Deploy** | `genlayer deploy` | deploy contract to Studionet over a validated https RPC | opt-in; guardrail gate |

### 1.3 Components

```
Pipeline/
├── pyproject.toml                 # package metadata, deps, console entrypoints
├── README.md                      # this blueprint
├── Makefile                       # local entrypoints (make install / ci / doctor / selftest …)
├── .env.example                   # env-var contract (validated by guardrails)
├── config/
│   ├── gltest.config.yaml         # network definitions (localnet/studionet/testnet) via ${env}
│   └── pipeline.example.toml      # per-project config template
├── src/genlayer_pipeline/         # the installable package
│   ├── run_pipeline.py            # ★ orchestration harness (stdlib-only)
│   ├── pipeline_config.py         # dynamic contract/config resolution
│   ├── guardrails.py              # env mapping, RPC security, error taxonomy
│   ├── deployment.py              # ledger + rollback
│   ├── report.py                  # execution analytics
│   └── __main__.py                # `python -m genlayer_pipeline`
├── selftests/                     # toolkit regression suite (zero-trace guard)
└── .github/workflows/
    └── ci-cd.yml                  # 5-job GitHub Actions pipeline (Stage 0 = compliance)
```

---

## 2. Test automation harness (`genlayer_pipeline/run_pipeline.py`)

A single orchestrator drives all four stages with these guarantees:

- **Zero silent failures.** Every subprocess is run with full stdout/stderr
  capture, a hard timeout (`--timeout`, default 900 s), and an explicit exit-code
  check. A non-zero exit, a timeout (124), or a missing tool (127) each abort with
  a structured, tailed error.
- **Reproducible, structured logs.** Each stage writes `<name>.log`; the run
  writes `pipeline_summary.json` (machine-readable) and `junit-direct.xml`
  (consumable by any CI test reporter) to `<root>/artifacts/pipeline/`.
- **Mock environment for tests.** The test stage injects an isolated loopback
  `localnet` env and blanks `GENLAYER_PRIVATE_KEY`, so a stray secret can never
  redirect a test run at a live network. Disable with `--no-mock-env`.
- **Fail-fast, with a diagnostic mode.** Default aborts on first failure;
  `--continue-on-error` runs every stage for a full report.
- **Root auto-detection.** Walks up to find the project root (`contracts/` +
  `tests/`), so it works vendored in-repo or promoted to its own repository.

### Usage

```bash
make ci                                   # lint -> test -> build (what PRs run)
make plan                                 # dry-run: print the 4-stage plan
genlayer-pipeline --stages lint,test --root <proj>
genlayer-pipeline --from build --root <proj>   # build -> deploy
genlayer-pipeline --stages all --json --root <proj>   # NDJSON stream
genlayer-pipeline --stages deploy --root <proj>   # requires validated env
```

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | all selected stages passed |
| `1` | a stage failed (lint/test/build/deploy regression) |
| `2` | guardrail / configuration error — fix the environment, then retry |
| `3` | usage / internal error |

Distinguishing **2** (mis-configuration, retry won't help) from **1** (genuine
regression) lets CI route alerts correctly.

---

## 3. Configuration guardrails (`genlayer_pipeline/guardrails.py`)

### 3.1 Environment-variable mapping

| Variable | Required for | Format (validated) |
|----------|--------------|--------------------|
| `GENLAYER_CHAIN_TYPE` | deploy | `localnet\|studionet\|testnet_asimov\|testnet_bradbury` |
| `GENLAYER_RPC_URL` | deploy | `https?://…` (https enforced off-local) |
| `GENLAYER_PRIVATE_KEY` | deploy | `0x` + 64 hex; **secret**, never logged |
| `GENLAYER_CONTRACT_PATH` | optional | `*.py` |

All missing/malformed vars are reported **at once** so the environment is fixed in
one pass. Secret values are always masked (`0xab…cd (len=66)`) in any output.

### 3.2 RPC security

- Any non-local chain **must** use `https` — the runner refuses to send a signed
  transaction over plaintext.
- Plain `http` is tolerated **only** on `localnet` **and only** against loopback.
- A remote chain pointed at loopback is rejected as an obvious mis-config.
- The signer key is passed to `genlayer deploy` via **env, never argv** (argv is
  visible in process listings and CI logs).

### 3.3 Error-handling protocol (zero silent failures)

1. Guardrails run **before** any network I/O; failure → exit 2, nothing deployed.
2. Every stage subprocess is captured + timed + exit-checked; no `|| true`.
3. Deploy is **opt-in** (workflow dispatch input or `v*` tag) and protected by a
   GitHub `environment: studionet` gate (required reviewers + scoped secrets).
4. `concurrency: deploy-studionet` (no cancel) prevents overlapping deploys.

---

## 4. CI/CD workflow (`.github/workflows/ci-cd.yml`)

Five jobs — `compliance → lint → test → build → deploy-studionet` — chained with
`needs:`, so nothing runs until the upstream gate is green.

**Stage 0 · Compliance (pre-flight gate).** Runs first and blocks the whole
pipeline: `make selftest` (the zero-trace guard + config/guardrail/rollback
regression suite) plus `--self-check`. Any violation fails the build **instantly**,
before a single contract is linted or tested. It needs only `pytest` (no GenLayer
toolchain), so the gate is fast.

Triggers: PRs and pushes to `main` run stages 0–3; deploy runs only on a manual
`workflow_dispatch` with `deploy: true`, or on a `v*` tag. Artifacts (logs, JUnit
report, ABI schema, `frontend/dist`) are uploaded with tiered retention
(14–90 days).

**Activation.** This is the repo root, so the workflow is already at
`.github/workflows/ci-cd.yml` and runs as-is. Set repo secrets
`STUDIONET_RPC_URL` and `STUDIONET_DEPLOYER_KEY` on the `studionet` environment
before enabling the deploy stage.

---

## 5. Quick start

Install the CLI (editable, with the GenLayer toolchain extra):

```bash
cd /Users/ehs4n/Pipeline
pip install -e '.[toolchain]'          # or: make install
```

This puts three console commands on your PATH:

| Command | Purpose |
|---|---|
| `genlayer-pipeline` (alias `pipeline-cli`) | run the pipeline stages |
| `genlayer-pipeline-report` | render the analytics report |
| `python -m genlayer_pipeline` | module-form equivalent of the CLI |

Then run it against any GenLayer project:

```bash
genlayer-pipeline                                # target = current dir
genlayer-pipeline --root /path/to/genlayer-app   # target = external project
genlayer-pipeline --stages lint,test --root .    # pick stages
genlayer-pipeline --self-check                   # generic-toolkit assertion

# Makefile wrappers (identical commands):
make ci                               # lint + test + build against the current dir
make ci TARGET=/path/to/genlayer-app  # …or against an external GenLayer project
```

To deploy locally (after populating `.env` from `.env.example`):

```bash
set -a && source .env && set +a
make deploy
```

---

## 6. Step 2 — Advanced error handling & artifact management

### 6.1 Execution analytics (`genlayer_pipeline/report.py`)

At the end of **every** run the harness parses its own artifacts into a single
analytics report — no extra command required:

- `junit-direct.xml` → totals, pass rate, **slowest tests**, per-failure messages
- `pipeline_summary.json` → per-stage status / duration / exit code
- `events.ndjson` → durable event timeline (written every run)
- `deployments/ledger.json` → current live address + last rollback

Outputs `report.md` and `report.json` to the artifacts dir and prints a console
summary. Regenerate any time from the last run without re-running the pipeline:

```bash
make report        # text to console
make report-md     # Markdown
genlayer-pipeline-report --artifacts-dir artifacts/pipeline --format json
```

### 6.2 Failure recovery & rollback (Studionet deploys)

GenLayer contracts are immutable, so "rollback" is **reference-level**: the
pipeline maintains a `current` pointer (the deployment ledger) that is only
advanced to a new address after it **both** broadcasts *and* passes a post-deploy
smoke check. The deploy stage now runs:

```
import key → unlock → deploy (retry×N, linear backoff)
   → parse deployed address
   → smoke verify  (genlayer schema <addr>)
   → promote to `current`      ✅ on success
   → ROLLBACK (keep previous)  ⟲ on broadcast OR verify failure
```

Two rollback triggers, both keeping the last-known-good address live for clients:

| Trigger | When | Effect |
|---|---|---|
| **Broadcast failure** | deploy fails after all retries | `current` unchanged; failure + `rolled_back` marker appended to ledger |
| **Verification failure** | deployed but `schema <addr>` smoke check fails | new address recorded as `failed`; `current` stays on previous good |

Tunables: `--deploy-retries` (default 2), `--deploy-backoff` (base seconds,
linear), `--no-verify-deploy`. Ledger location: `<artifacts>/deployments/ledger.json`
or `PIPELINE_LEDGER_PATH` / `--ledger-path`. In CI (ephemeral runners) persist the
ledger as a build artifact or a state branch so `current` survives across runs.

```bash
make ledger        # show current live address + deploy/rollback history
```

### 6.3 Advanced automation — aggregation, trend, failure triggers

Every run now also produces (all under the artifacts dir):

| Artifact | Purpose |
|---|---|
| `aggregate.log` | all per-stage logs concatenated with section headers — one file to grep/attach/ship |
| `history.ndjson` | one record per run (pass/fail, per-stage status, durations, git sha) for **cross-run trend analytics** |
| `alerts/<stage>.alert.json` | structured alert written on any stage failure |

The analytics report gains a **Trend** line (`✓✓✗✓…  N/M passed` over the last 10
runs) and a **Failure alerts** section.

**Error-handling triggers.** On *any* stage failure the harness fires a
configurable hook — set `[triggers].on_failure` in `pipeline.toml` or the
`PIPELINE_ON_FAILURE` env var. The hook receives context via env
(`PIPELINE_FAILED_STAGE`, `PIPELINE_EXIT_CODE`, `PIPELINE_LOG`, `PIPELINE_ERROR`)
so you can wire Slack / webhook / PagerDuty without the toolkit hardcoding any
provider. Triggers are best-effort and never mask the original failure.

---

## 7. Local verification steps (via the Makefile)

Run these from `/Users/ehs4n/Pipeline` to verify the whole system locally.

```bash
# 0. install the CI toolchain (one time)
make install

# 1. see the full 4-stage plan without executing anything (point at any project)
make plan TARGET=/path/to/genlayer-app

# 2. run the CI stages against a target GenLayer project
make ci   TARGET=/path/to/genlayer-app   # lint → test → build (auto-prints analytics)

# 3. inspect the generated analytics + artifacts (always local to this workspace)
make report                 # execution analytics (test totals, slowest, failures)
ls artifacts/pipeline/      # report.md, report.json, junit-direct.xml,
                            # pipeline_summary.json, events.ndjson, *.log

# 4. run individual stages
make lint  TARGET=/path/to/genlayer-app
make test  TARGET=/path/to/genlayer-app
make build TARGET=/path/to/genlayer-app

# 5. deploy + rollback (needs a funded key in .env)
set -a && source .env && set +a
make deploy                 # retry/verify/rollback-guarded Studionet deploy
make ledger                 # confirm the current live address advanced
```

**What "verified" looks like**

| Check | Expected |
|---|---|
| `make ci` exit code | `0`; console shows `[PASS]` for lint/test/build + `PASS ✓` analytics |
| `make report` | `pass rate: 100.0%`, 16 direct-mode tests, slowest tests listed |
| `artifacts/pipeline/report.md` | exists and matches the console report |
| RPC guardrail | `GENLAYER_CHAIN_TYPE=studionet GENLAYER_RPC_URL=http://… make deploy` → exit `2`, refuses plaintext |
| Rollback | a failed deploy leaves `make ledger` `current` on the previous good address with a `rolled_back` entry |

Exit codes: `0` pass · `1` stage failure · `2` configuration/guardrail error ·
`3` usage/internal error.

---

## 8. Building distribution artifacts

Build and validate a wheel + sdist locally (needs the `build` extra:
`pip install -e '.[build]'`):

```bash
make build-dist        # python -m build → dist/*.whl + dist/*.tar.gz
make validate-dist     # twine check + wheel-contents inspection + temp-venv install
make release-check     # build-dist + validate-dist in one shot
make dist-clean        # remove dist/ build/ *.egg-info
```

`make validate-dist` (`tools/validate_dist.sh`) asserts the artifacts are
publish-ready: `twine check` passes, the wheel bundles every package module and
all three console entrypoints, and both the **wheel** and the **sdist** install
cleanly into throwaway virtualenvs where `genlayer-pipeline --help`,
`python -m genlayer_pipeline`, and `--self-check` all succeed.

Outputs (`dist/`, `build/`, `*.egg-info`) are git-ignored.
# PipeLine
