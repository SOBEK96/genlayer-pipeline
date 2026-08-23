#!/usr/bin/env python3
"""
report.py — execution analytics for the GenLayer CI/CD pipeline.

Parses the artifacts produced by run_pipeline.py into a single, readable
execution-analytics report:

  * junit-direct.xml       -> test totals, pass rate, slowest tests, failures
  * pipeline_summary.json  -> per-stage status / duration / exit code
  * events.ndjson          -> event timeline (optional)
  * deployments/ledger.json-> current live address + last rollback (optional)

Renders to text (console), Markdown (report.md), or JSON (report.json). The
runner calls `generate()` automatically at the end of every run; it is also a
standalone CLI:

    python scripts/report.py                         # text to stdout
    python scripts/report.py --format md             # write report.md
    python scripts/report.py --artifacts-dir path/to/artifacts --format json
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


# --------------------------------------------------------------------------- #
# Data model                                                                  #
# --------------------------------------------------------------------------- #


@dataclass
class TestCase:
    name: str
    classname: str
    time: float
    outcome: str            # passed | failed | error | skipped
    message: str = ""


@dataclass
class TestAnalytics:
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration_s: float = 0.0
    cases: list[TestCase] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        run = self.total - self.skipped
        return (self.passed / run * 100.0) if run else 0.0

    def slowest(self, n: int = 5) -> list[TestCase]:
        return sorted(self.cases, key=lambda c: c.time, reverse=True)[:n]

    def failures(self) -> list[TestCase]:
        return [c for c in self.cases if c.outcome in ("failed", "error")]


@dataclass
class ReportData:
    overall_passed: bool = True
    project_root: str = ""
    generated_at: str = ""
    stages: list[dict] = field(default_factory=list)
    tests: TestAnalytics = field(default_factory=TestAnalytics)
    timeline: list[dict] = field(default_factory=list)
    deployment: dict | None = None
    history: list[dict] = field(default_factory=list)
    alerts: list[dict] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Parsers                                                                     #
# --------------------------------------------------------------------------- #


def parse_junit(path: Path) -> TestAnalytics:
    a = TestAnalytics()
    if not path.exists():
        return a
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return a
    suites = [root] if root.tag == "testsuite" else root.findall(".//testsuite")
    for suite in suites:
        for tc in suite.findall("testcase"):
            t = float(tc.get("time", "0") or 0)
            outcome, message = "passed", ""
            if (fail := tc.find("failure")) is not None:
                outcome = "failed"
                message = (fail.get("message") or fail.text or "").strip()
            elif (err := tc.find("error")) is not None:
                outcome = "error"
                message = (err.get("message") or err.text or "").strip()
            elif tc.find("skipped") is not None:
                outcome = "skipped"
            case = TestCase(
                name=tc.get("name", "?"),
                classname=tc.get("classname", ""),
                time=t, outcome=outcome, message=message[:300],
            )
            a.cases.append(case)
            a.total += 1
            a.duration_s += t
            a.__dict__[{"passed": "passed", "failed": "failed",
                        "error": "errors", "skipped": "skipped"}[outcome]] += 1
    return a


def parse_summary(path: Path) -> tuple[list[dict], bool, str, str]:
    if not path.exists():
        return [], True, "", ""
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return [], True, "", ""
    return (
        data.get("results", []),
        bool(data.get("passed", True)),
        data.get("project_root", ""),
        data.get("generated_at", ""),
    )


def parse_ndjson(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def parse_ledger(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    history = data.get("history", [])
    rollbacks = [h for h in history if h.get("status") == "rolled_back"]
    return {
        "current": data.get("current"),
        "deploy_count": sum(1 for h in history if h.get("status") == "active"),
        "failure_count": sum(1 for h in history if h.get("status") == "failed"),
        "last_rollback": rollbacks[-1] if rollbacks else None,
    }


# --------------------------------------------------------------------------- #
# Aggregation                                                                 #
# --------------------------------------------------------------------------- #


def parse_alerts(alerts_dir: Path) -> list[dict]:
    if not alerts_dir.is_dir():
        return []
    out = []
    for f in sorted(alerts_dir.glob("*.alert.json")):
        try:
            out.append(json.loads(f.read_text()))
        except (OSError, json.JSONDecodeError):
            continue
    return out


def build_report(artifacts_dir: Path) -> ReportData:
    stages, overall, root, generated = parse_summary(artifacts_dir / "pipeline_summary.json")
    return ReportData(
        overall_passed=overall,
        project_root=root,
        generated_at=generated,
        stages=stages,
        tests=parse_junit(artifacts_dir / "junit-direct.xml"),
        timeline=parse_ndjson(artifacts_dir / "events.ndjson"),
        deployment=parse_ledger(artifacts_dir / "deployments" / "ledger.json"),
        history=parse_ndjson(artifacts_dir / "history.ndjson"),
        alerts=parse_alerts(artifacts_dir / "alerts"),
    )


# --------------------------------------------------------------------------- #
# Renderers                                                                   #
# --------------------------------------------------------------------------- #


def _bar(pct: float, width: int = 20) -> str:
    filled = int(round(pct / 100 * width))
    return "█" * filled + "░" * (width - filled)


def render_text(r: ReportData) -> str:
    t = r.tests
    L: list[str] = []
    verdict = "PASS ✓" if r.overall_passed else "FAIL ✗"
    L.append("═" * 64)
    L.append(f" GenLayer Pipeline — Execution Analytics     [{verdict}]")
    L.append("═" * 64)
    if r.generated_at:
        L.append(f" generated: {r.generated_at}")
    L.append("")
    L.append(" Stages")
    L.append(" " + "-" * 62)
    for s in r.stages:
        badge = {"passed": "PASS", "failed": "FAIL", "skipped": "SKIP"}.get(s["status"], "?")
        code = s.get("exit_code")
        L.append(f"   [{badge}] {s['name']:<16} {s['duration_s']:>7.2f}s"
                 f"   exit={code}")
    L.append("")
    L.append(" Test analytics (direct mode)")
    L.append(" " + "-" * 62)
    if t.total:
        L.append(f"   total={t.total}  passed={t.passed}  failed={t.failed}"
                 f"  errors={t.errors}  skipped={t.skipped}")
        L.append(f"   pass rate: {t.pass_rate:5.1f}%  {_bar(t.pass_rate)}")
        L.append(f"   test time: {t.duration_s:.2f}s")
        L.append("")
        L.append("   slowest tests:")
        for c in t.slowest():
            L.append(f"     {c.time*1000:7.1f} ms  {c.name}")
        if t.failures():
            L.append("")
            L.append("   FAILURES:")
            for c in t.failures():
                L.append(f"     ✗ {c.name}")
                if c.message:
                    L.append(f"         {c.message.splitlines()[0]}")
    else:
        L.append("   (no junit report found)")
    if r.deployment:
        d = r.deployment
        L.append("")
        L.append(" Deployment")
        L.append(" " + "-" * 62)
        cur = d.get("current")
        L.append(f"   current live: {cur['address'] if cur else '(none)'}")
        L.append(f"   deploys={d['deploy_count']}  failures={d['failure_count']}")
        if d.get("last_rollback"):
            rb = d["last_rollback"]
            L.append(f"   ⟲ last rollback: kept {rb.get('address') or '(none)'}"
                     f"  — {rb.get('reason','')}")
    if r.alerts:
        L.append("")
        L.append(" ⚠ Failure alerts (this run)")
        L.append(" " + "-" * 62)
        for a in r.alerts:
            L.append(f"   ✗ {a.get('stage')}  exit={a.get('exit_code')}  → {a.get('log')}")
    if len(r.history) > 1:
        L.append("")
        L.append(f" Trend (last {min(len(r.history), 10)} runs)")
        L.append(" " + "-" * 62)
        recent = r.history[-10:]
        spark = "".join("✓" if h.get("passed") else "✗" for h in recent)
        passes = sum(1 for h in recent if h.get("passed"))
        L.append(f"   {spark}   {passes}/{len(recent)} passed")
    L.append("═" * 64)
    return "\n".join(L)


def render_markdown(r: ReportData) -> str:
    t = r.tests
    verdict = "✅ PASS" if r.overall_passed else "❌ FAIL"
    L = [f"# GenLayer Pipeline — Execution Analytics  {verdict}", ""]
    if r.generated_at:
        L.append(f"_Generated: {r.generated_at}_")
    L += ["", "## Stages", "", "| Stage | Status | Duration | Exit |", "|---|---|---:|---:|"]
    for s in r.stages:
        icon = {"passed": "✅", "failed": "❌", "skipped": "⏭️"}.get(s["status"], "❔")
        L.append(f"| `{s['name']}` | {icon} {s['status']} | {s['duration_s']:.2f}s "
                 f"| {s.get('exit_code')} |")
    L += ["", "## Test analytics (direct mode)", ""]
    if t.total:
        L += [
            f"- **Total:** {t.total}  •  **Passed:** {t.passed}  •  "
            f"**Failed:** {t.failed}  •  **Errors:** {t.errors}  •  "
            f"**Skipped:** {t.skipped}",
            f"- **Pass rate:** {t.pass_rate:.1f}%",
            f"- **Test time:** {t.duration_s:.2f}s",
            "",
            "### Slowest tests", "",
            "| Test | Time |", "|---|---:|",
        ]
        for c in t.slowest():
            L.append(f"| `{c.name}` | {c.time*1000:.1f} ms |")
        if t.failures():
            L += ["", "### Failures", ""]
            for c in t.failures():
                L.append(f"- ❌ `{c.name}` — {c.message.splitlines()[0] if c.message else ''}")
    else:
        L.append("_No junit report found._")
    if r.deployment:
        d = r.deployment
        cur = d.get("current")
        L += ["", "## Deployment", "",
              f"- **Current live address:** `{cur['address'] if cur else '(none)'}`",
              f"- **Successful deploys:** {d['deploy_count']}  •  "
              f"**Failed:** {d['failure_count']}"]
        if d.get("last_rollback"):
            rb = d["last_rollback"]
            L.append(f"- ⟲ **Last rollback:** kept `{rb.get('address') or '(none)'}` "
                     f"— {rb.get('reason','')}")
    if r.alerts:
        L += ["", "## ⚠ Failure alerts (this run)", ""]
        for a in r.alerts:
            L.append(f"- ❌ `{a.get('stage')}` exit={a.get('exit_code')} — `{a.get('log')}`")
    if len(r.history) > 1:
        recent = r.history[-10:]
        spark = "".join("✓" if h.get("passed") else "✗" for h in recent)
        passes = sum(1 for h in recent if h.get("passed"))
        L += ["", f"## Trend (last {len(recent)} runs)", "",
              f"`{spark}` — {passes}/{len(recent)} passed"]
    L.append("")
    return "\n".join(L)


def render_json(r: ReportData) -> str:
    return json.dumps({
        "overall_passed": r.overall_passed,
        "generated_at": r.generated_at,
        "stages": r.stages,
        "tests": {
            "total": r.tests.total, "passed": r.tests.passed,
            "failed": r.tests.failed, "errors": r.tests.errors,
            "skipped": r.tests.skipped, "pass_rate": round(r.tests.pass_rate, 2),
            "duration_s": round(r.tests.duration_s, 3),
            "slowest": [{"name": c.name, "time_ms": round(c.time * 1000, 1)}
                        for c in r.tests.slowest()],
            "failures": [{"name": c.name, "message": c.message}
                         for c in r.tests.failures()],
        },
        "deployment": r.deployment,
        "alerts": r.alerts,
        "trend": {
            "runs": len(r.history),
            "recent": [{"ts": h.get("ts"), "passed": h.get("passed")}
                       for h in r.history[-10:]],
        },
    }, indent=2)


# --------------------------------------------------------------------------- #
# Entry points                                                                #
# --------------------------------------------------------------------------- #


def generate(artifacts_dir: Path, fmt: str = "md", write: bool = True) -> str:
    """Build the report and (optionally) persist it. Returns rendered content.

    Always writes report.json + report.md alongside; returns the requested fmt.
    """
    r = build_report(artifacts_dir)
    rendered = {"text": render_text, "md": render_markdown, "json": render_json}[fmt](r)
    if write:
        (artifacts_dir / "report.md").write_text(render_markdown(r))
        (artifacts_dir / "report.json").write_text(render_json(r))
    return rendered


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="GenLayer pipeline analytics report")
    p.add_argument("--artifacts-dir", default=None,
                   help="artifacts dir (default: <cwd>/artifacts/pipeline)")
    p.add_argument("--format", choices=["text", "md", "json"], default="text")
    p.add_argument("--no-write", action="store_true", help="print only; do not write files")
    args = p.parse_args(argv)

    if args.artifacts_dir:
        art = Path(args.artifacts_dir)
    else:
        art = Path.cwd() / "artifacts" / "pipeline"
        if not art.exists():
            print("no artifacts dir found; run the pipeline first", file=sys.stderr)
            return 1

    print(generate(art, fmt=args.format, write=not args.no_write))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
