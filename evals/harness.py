"""Run the cases and score what comes back.

The harness deliberately drives DEEP's *real* machinery: the tool descriptions
come from `DeepToolRegistry.describe_tools()`, the system prompt from
`AsyncBrain._build_system_prompt()`, and the model's reply is parsed by
`_extract_tool_json` and `_parse_tool_call`. Reimplementing any of those would
make the score measure the harness rather than the assistant, and would go
stale the moment someone edited the prompt — which is precisely the change this
exists to catch.

What is scored, and why each one is separate:

* **correct** — the expected tool, or one listed as `also_acceptable`.
* **wrong_tool** — a real tool, but not one that answers the question. Usually
  a description collision between two overlapping tools.
* **over_trigger** — called a tool on a case that wanted a direct answer. The
  expensive failure: it burns a loop and a rate limit on every chatty turn.
* **under_trigger** — answered from training data when a tool was needed. The
  dangerous one for security work, where recalled facts are stale by definition.
* **invalid_call** — malformed JSON or a hallucinated tool name. DEEP recovers
  from these in one corrective loop, so they cost latency rather than accuracy —
  tracked separately so that distinction survives into the report.

`args_ok` is only meaningful on a correct call, so it is scored over correct
calls rather than over all cases. A tool-accuracy figure that quietly included
argument errors would flatter a model that finds the right tool and then feeds
it nonsense.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from evals.cases import CASES, Case
from evals.models import Model

#: Outcome labels. Ordered worst-to-best for reporting.
OUTCOMES = ("invalid_call", "over_trigger", "under_trigger", "wrong_tool", "correct")


@dataclass(slots=True)
class CaseResult:
    """What one case did."""

    case_id: str
    outcome: str
    expected_tool: Optional[str]
    actual_tool: Optional[str]
    args: Dict[str, Any] = field(default_factory=dict)
    missing_args: Dict[str, str] = field(default_factory=dict)
    #: True when the tool was in `also_acceptable` rather than `expected_tool`.
    via_fallback: bool = False
    error: str = ""
    raw_reply: str = ""
    elapsed_ms: int = 0

    @property
    def correct(self) -> bool:
        return self.outcome == "correct"

    @property
    def args_ok(self) -> bool:
        return self.correct and not self.missing_args

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Report:
    """The suite's result. Comparable across runs; that is the whole point."""

    model: str
    results: List[CaseResult]
    started_at: str
    elapsed_s: float

    # ── headline numbers ─────────────────────────────────────────────────────

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def tool_accuracy(self) -> float:
        """Share of cases whose outcome was the right call (or a no-call)."""
        return self._share(r.correct for r in self.results)

    @property
    def arg_accuracy(self) -> float:
        """Of the calls that picked the right tool, how many got the args right.

        Scored over correct *tool calls* only — a case expecting no tool has no
        arguments to get right, and counting it as a pass would inflate this.
        """
        scoped = [r for r in self.results if r.correct and r.actual_tool]
        if not scoped:
            return 1.0
        return round(sum(1 for r in scoped if r.args_ok) / len(scoped), 3)

    @property
    def over_trigger_rate(self) -> float:
        """Of the cases that wanted no tool, how many got one anyway."""
        scoped = [r for r in self.results if r.expected_tool is None]
        if not scoped:
            return 0.0
        return round(sum(1 for r in scoped if r.outcome == "over_trigger") / len(scoped), 3)

    @property
    def under_trigger_rate(self) -> float:
        scoped = [r for r in self.results if r.expected_tool is not None]
        if not scoped:
            return 0.0
        return round(sum(1 for r in scoped if r.outcome == "under_trigger") / len(scoped), 3)

    @property
    def invalid_call_rate(self) -> float:
        return self._share(r.outcome == "invalid_call" for r in self.results)

    @property
    def fallback_rate(self) -> float:
        """Correct, but via `also_acceptable` rather than the expected tool.

        Worth watching on its own: a rising fallback rate is a description
        drifting toward a neighbour's territory, and it is invisible in a
        headline accuracy that counts both as a pass.
        """
        return self._share(r.via_fallback for r in self.results)

    def _share(self, flags) -> float:
        flags = list(flags)
        return round(sum(1 for f in flags if f) / len(flags), 3) if flags else 0.0

    # ── breakdowns ───────────────────────────────────────────────────────────

    def by_outcome(self) -> Dict[str, int]:
        counts = {o: 0 for o in OUTCOMES}
        for r in self.results:
            counts[r.outcome] = counts.get(r.outcome, 0) + 1
        return counts

    def failures(self) -> List[CaseResult]:
        return [r for r in self.results if not r.correct or not r.args_ok]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "started_at": self.started_at,
            "elapsed_s": round(self.elapsed_s, 1),
            "total": self.total,
            "tool_accuracy": self.tool_accuracy,
            "arg_accuracy": self.arg_accuracy,
            "over_trigger_rate": self.over_trigger_rate,
            "under_trigger_rate": self.under_trigger_rate,
            "invalid_call_rate": self.invalid_call_rate,
            "fallback_rate": self.fallback_rate,
            "by_outcome": self.by_outcome(),
            "results": [r.to_dict() for r in self.results],
        }


# ── the run ──────────────────────────────────────────────────────────────────


def _brain_and_tools():
    """DEEP's real prompt builder and real registry.

    Imported lazily so `evals.cases` stays importable without DEEP's whole
    dependency tree — a contributor should be able to read and add cases
    without a working install.
    """
    from core.infrastructure.async_brain import AsyncBrain
    from core.tools.deep_registry import DeepToolRegistry

    tools = DeepToolRegistry()
    brain = AsyncBrain.__new__(AsyncBrain)  # prompt building needs no LLM
    brain.persona = None
    brain.llm = None
    return brain, tools


def _score(case: Case, name: Optional[str], args: Dict[str, Any], error: str) -> tuple:
    """(outcome, missing_args, via_fallback) for one parsed reply."""
    if error:
        return "invalid_call", {}, False

    if case.expected_tool is None:
        return ("over_trigger" if name else "correct"), {}, False

    if name is None:
        return "under_trigger", {}, False

    if name != case.expected_tool:
        if name in case.also_acceptable:
            return "correct", _missing(case, args), True
        return "wrong_tool", {}, False

    return "correct", _missing(case, args), False


def _missing(case: Case, args: Dict[str, Any]) -> Dict[str, str]:
    """Expected argument substrings that are not present anywhere in the args.

    Matched against every value rather than a specific key: models legitimately
    disagree about whether a URL belongs under `url` or `target`, and DEEP's own
    tools differ on that too. What matters is that the indicator survived the
    trip out of the sentence.
    """
    blob = " ".join(str(v) for v in args.values()).lower()
    return {k: v for k, v in case.expected_args.items() if v.lower() not in blob}


async def run_case(case: Case, model: Model, brain=None, tools=None) -> CaseResult:
    """Run one case through the real prompt and the real parser."""
    if brain is None or tools is None:
        brain, tools = _brain_and_tools()

    system_prompt = brain._build_system_prompt(tools.describe_tools())
    started = time.monotonic()
    try:
        reply = await model.complete(system_prompt, case.prompt)
    except Exception as exc:  # noqa: BLE001 - a dead model is a result, not a crash
        return CaseResult(
            case_id=case.id, outcome="invalid_call", expected_tool=case.expected_tool,
            actual_tool=None, error=f"{type(exc).__name__}: {exc}",
            elapsed_ms=int((time.monotonic() - started) * 1000),
        )
    elapsed_ms = int((time.monotonic() - started) * 1000)

    name: Optional[str] = None
    args: Dict[str, Any] = {}
    error = ""
    if "[TOOL:" in reply:
        raw = brain._extract_tool_json(reply[reply.find("[TOOL:"):])
        ok, name_or_err, parsed = brain._parse_tool_call(raw, tools)
        if ok:
            name, args = name_or_err, parsed
        else:
            error = name_or_err

    outcome, missing, via_fallback = _score(case, name, args, error)
    return CaseResult(
        case_id=case.id, outcome=outcome, expected_tool=case.expected_tool,
        actual_tool=name, args=args, missing_args=missing, via_fallback=via_fallback,
        error=error, raw_reply=reply[:400], elapsed_ms=elapsed_ms,
    )


async def run_suite(
    model: Model,
    cases: Sequence[Case] = tuple(CASES),
    *,
    concurrency: int = 4,
    on_result=None,
) -> Report:
    """Run every case. Concurrency is bounded — a local model will thrash otherwise."""
    from datetime import datetime, timezone

    brain, tools = _brain_and_tools()
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()

    semaphore = asyncio.Semaphore(max(1, concurrency))
    results: List[Optional[CaseResult]] = [None] * len(cases)

    async def one(index: int, case: Case) -> None:
        async with semaphore:
            result = await run_case(case, model, brain, tools)
        results[index] = result
        if on_result is not None:
            on_result(result)

    await asyncio.gather(*(one(i, c) for i, c in enumerate(cases)))
    return Report(
        model=getattr(model, "name", type(model).__name__),
        results=[r for r in results if r is not None],
        started_at=started_at,
        elapsed_s=time.monotonic() - started,
    )


def render(report: Report, *, verbose: bool = False) -> str:
    """A report someone will actually read after a run."""
    by = report.by_outcome()
    lines = [
        f"model            {report.model}",
        f"cases            {report.total}  ({report.elapsed_s:.1f}s)",
        "",
        f"tool accuracy    {report.tool_accuracy:.0%}",
        f"arg accuracy     {report.arg_accuracy:.0%}   (of correct tool calls)",
        f"over-trigger     {report.over_trigger_rate:.0%}   (of cases wanting no tool)",
        f"under-trigger    {report.under_trigger_rate:.0%}   (of cases wanting a tool)",
        f"invalid calls    {report.invalid_call_rate:.0%}",
        f"via fallback     {report.fallback_rate:.0%}   (correct, but not the expected tool)",
        "",
        "  " + "  ".join(f"{k}={v}" for k, v in by.items() if v),
    ]

    failures = report.failures()
    if failures:
        lines += ["", f"failures ({len(failures)}):"]
        cases = {c.id: c for c in CASES}
        for r in failures:
            expected = r.expected_tool or "(no tool)"
            actual = r.actual_tool or ("(no tool)" if not r.error else "(invalid)")
            lines.append(f"  {r.case_id}: expected {expected}, got {actual}  [{r.outcome}]")
            if r.missing_args:
                lines.append(f"      args missing: {r.missing_args}")
            if r.error:
                lines.append(f"      {r.error[:140]}")
            rationale = getattr(cases.get(r.case_id), "rationale", "")
            if rationale:
                lines.append(f"      why this case exists: {rationale[:160]}")
            if verbose and r.raw_reply:
                lines.append(f"      reply: {r.raw_reply[:200]!r}")
    else:
        lines += ["", "no failures."]
    return "\n".join(lines)


def to_json(report: Report) -> str:
    return json.dumps(report.to_dict(), indent=2)
