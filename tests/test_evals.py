"""Tests for the eval harness itself.

An eval suite nobody can trust is worse than none: it produces a number that
gets quoted. These pin the scoring against a scripted model, so the harness is
checked without a live LLM and without the score depending on one.

What matters here is that each failure mode is scored *distinctly*. A harness
that lumped over-triggering in with wrong-tool would report one number where
two different fixes are needed — reword a description versus add a negative
instruction to the prompt.
"""
from __future__ import annotations

import json

import pytest

from evals import cases as case_module
from evals.cases import CASES, Case, by_tag
from evals.harness import Report, render, run_case, run_suite, to_json
from evals.models import CallableModel, ScriptedModel


def _tool_reply(name: str, **args) -> str:
    return f'Let me check. [TOOL:{{"name": "{name}", "args": {json.dumps(args)}}}]'


@pytest.fixture(scope="module")
def machinery():
    """DEEP's real brain + registry, built once — importing them is slow."""
    from evals.harness import _brain_and_tools

    return _brain_and_tools()


# ── the case set itself ──────────────────────────────────────────────────────


def test_every_expected_tool_actually_exists(machinery):
    """A case naming a tool that was renamed away fails forever and teaches nothing."""
    _, tools = machinery
    real = set(tools.list_tools())

    for case in CASES:
        if case.expected_tool is not None:
            assert case.expected_tool in real, f"{case.id} expects unknown tool"
        for alt in case.also_acceptable:
            assert alt in real, f"{case.id} lists unknown fallback {alt}"


def test_case_ids_are_unique():
    ids = [c.id for c in CASES]
    assert len(ids) == len(set(ids))


def test_the_suite_covers_over_triggering():
    """Without negative cases the suite rewards a model that calls tools always."""
    negatives = [c for c in CASES if c.expected_tool is None]
    assert len(negatives) >= 4, "too few negative cases to detect over-triggering"


def test_urlscan_work_is_covered():
    assert len(by_tag("urlscan")) >= 4


# ── scoring ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_expected_tool_scores_correct(machinery):
    brain, tools = machinery
    case = Case(id="t", prompt="check https://x.test", expected_tool="url_lookup",
                expected_args={"url": "x.test"})
    model = ScriptedModel({"check": _tool_reply("url_lookup", url="https://x.test")})

    result = await run_case(case, model, brain, tools)
    assert result.outcome == "correct"
    assert result.args_ok is True
    assert result.via_fallback is False


@pytest.mark.asyncio
async def test_a_different_real_tool_is_wrong_tool_not_invalid(machinery):
    brain, tools = machinery
    case = Case(id="t", prompt="check https://x.test", expected_tool="url_lookup")
    model = ScriptedModel({"check": _tool_reply("get_time")})

    result = await run_case(case, model, brain, tools)
    assert result.outcome == "wrong_tool"
    assert result.actual_tool == "get_time"


@pytest.mark.asyncio
async def test_an_acceptable_alternative_passes_but_is_flagged(machinery):
    """Counted correct, tracked separately — a rising fallback rate is drift."""
    brain, tools = machinery
    case = Case(id="t", prompt="check it", expected_tool="url_lookup",
                also_acceptable=("threat_lookup",))
    model = ScriptedModel({"check": _tool_reply("threat_lookup", target="x.test")})

    result = await run_case(case, model, brain, tools)
    assert result.outcome == "correct"
    assert result.via_fallback is True


@pytest.mark.asyncio
async def test_calling_a_tool_when_none_was_wanted_is_over_trigger(machinery):
    brain, tools = machinery
    case = Case(id="t", prompt="what is a CVE", expected_tool=None)
    model = ScriptedModel({"cve": _tool_reply("cve_intel", cve_id="CVE-2021-44228")})

    result = await run_case(case, model, brain, tools)
    assert result.outcome == "over_trigger"


@pytest.mark.asyncio
async def test_answering_directly_when_a_tool_was_needed_is_under_trigger(machinery):
    brain, tools = machinery
    case = Case(id="t", prompt="is 1.2.3.4 malicious", expected_tool="threat_lookup")
    model = ScriptedModel({"malicious": "That address looks fine to me."})

    result = await run_case(case, model, brain, tools)
    assert result.outcome == "under_trigger"
    assert result.actual_tool is None


@pytest.mark.asyncio
async def test_a_hallucinated_tool_name_is_an_invalid_call(machinery):
    brain, tools = machinery
    case = Case(id="t", prompt="check it", expected_tool="url_lookup")
    model = ScriptedModel({"check": _tool_reply("scan_the_internet")})

    result = await run_case(case, model, brain, tools)
    assert result.outcome == "invalid_call"
    assert "Unknown tool" in result.error


@pytest.mark.asyncio
async def test_malformed_json_is_an_invalid_call_not_a_crash(machinery):
    brain, tools = machinery
    case = Case(id="t", prompt="check it", expected_tool="url_lookup")
    model = ScriptedModel({"check": '[TOOL:{"name": "url_lookup", "args": }]'})

    result = await run_case(case, model, brain, tools)
    assert result.outcome == "invalid_call"


@pytest.mark.asyncio
async def test_a_nested_argument_object_survives_extraction(machinery):
    """The naive parser truncated at the first ']'. Pin that it still doesn't."""
    brain, tools = machinery
    case = Case(id="t", prompt="check it", expected_tool="threat_lookup",
                expected_args={"target": "1.2.3.4"})
    model = ScriptedModel({
        "check": '[TOOL:{"name": "threat_lookup", "args": '
                 '{"target": "1.2.3.4", "opts": {"items": [1, 2]}}}]'
    })

    result = await run_case(case, model, brain, tools)
    assert result.outcome == "correct"
    assert result.args_ok is True


@pytest.mark.asyncio
async def test_the_right_tool_with_the_wrong_indicator_fails_on_args(machinery):
    """Tool accuracy alone would call this a pass, which is why args score apart."""
    brain, tools = machinery
    case = Case(id="t", prompt="check evil.test", expected_tool="url_lookup",
                expected_args={"url": "evil.test"})
    model = ScriptedModel({"check": _tool_reply("url_lookup", url="https://example.com")})

    result = await run_case(case, model, brain, tools)
    assert result.correct is True
    assert result.args_ok is False
    assert "url" in result.missing_args


@pytest.mark.asyncio
async def test_a_model_that_raises_is_a_result_not_a_crash(machinery):
    brain, tools = machinery

    def boom(_system, _user):
        raise RuntimeError("model is down")

    case = Case(id="t", prompt="check it", expected_tool="url_lookup")
    result = await run_case(case, CallableModel(boom), brain, tools)

    assert result.outcome == "invalid_call"
    assert "model is down" in result.error


@pytest.mark.asyncio
async def test_the_real_system_prompt_carries_the_tools(machinery):
    """If the harness stopped seeing real descriptions it would score a fiction."""
    brain, tools = machinery
    seen = ScriptedModel({})
    await run_case(Case(id="t", prompt="hello"), seen, brain, tools)

    system_prompt = seen.calls[0][0]
    assert "url_lookup" in system_prompt
    assert "threat_lookup" in system_prompt
    assert "[TOOL:" in system_prompt


# ── the report ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_perfect_run_reports_perfectly(machinery):
    suite = [
        Case(id="a", prompt="alpha", expected_tool="get_time"),
        Case(id="b", prompt="bravo", expected_tool=None),
    ]
    model = ScriptedModel({"alpha": _tool_reply("get_time")}, default="Hello.")

    report = await run_suite(model, suite, concurrency=2)
    assert report.tool_accuracy == 1.0
    assert report.over_trigger_rate == 0.0
    assert report.failures() == []
    assert "no failures" in render(report)


@pytest.mark.asyncio
async def test_rates_are_scoped_to_the_cases_they_describe(machinery):
    """over-trigger is of negative cases only; under-trigger of positive only."""
    suite = [
        Case(id="pos1", prompt="alpha", expected_tool="get_time"),
        Case(id="pos2", prompt="bravo", expected_tool="get_time"),
        Case(id="neg1", prompt="charlie", expected_tool=None),
    ]
    # pos1 answers directly (under-trigger); neg1 calls a tool (over-trigger).
    model = ScriptedModel(
        {"alpha": "It is late.", "bravo": _tool_reply("get_time"),
         "charlie": _tool_reply("get_time")},
    )

    report = await run_suite(model, suite, concurrency=1)
    assert report.under_trigger_rate == 0.5   # 1 of 2 positive cases
    assert report.over_trigger_rate == 1.0    # 1 of 1 negative case
    assert report.tool_accuracy == round(1 / 3, 3)


@pytest.mark.asyncio
async def test_arg_accuracy_ignores_cases_with_no_tool(machinery):
    """A no-tool case has no args; counting it would flatter the number."""
    suite = [
        Case(id="neg", prompt="alpha", expected_tool=None),
        Case(id="pos", prompt="bravo", expected_tool="url_lookup",
             expected_args={"url": "evil.test"}),
    ]
    model = ScriptedModel(
        {"alpha": "Sure.", "bravo": _tool_reply("url_lookup", url="https://other.test")}
    )

    report = await run_suite(model, suite, concurrency=1)
    assert report.tool_accuracy == 1.0     # both picked right
    assert report.arg_accuracy == 0.0      # the one call with args got them wrong


@pytest.mark.asyncio
async def test_the_report_round_trips_as_json(machinery):
    suite = [Case(id="a", prompt="alpha", expected_tool="get_time")]
    report = await run_suite(ScriptedModel({"alpha": _tool_reply("get_time")}), suite)

    payload = json.loads(to_json(report))
    assert payload["total"] == 1
    assert payload["results"][0]["case_id"] == "a"
    assert "tool_accuracy" in payload


@pytest.mark.asyncio
async def test_failures_explain_why_the_case_exists(machinery):
    """A failing eval whose point nobody remembers gets deleted, not fixed."""
    real = next(c for c in CASES if c.rationale and c.expected_tool)
    model = ScriptedModel({}, default="No tool for me.")

    report = await run_suite(model, [real], concurrency=1)
    text = render(report)
    assert real.id in text
    assert real.rationale[:40] in text


@pytest.mark.asyncio
async def test_a_scripted_run_is_labelled_as_not_a_real_model(machinery):
    """A scripted score must never be mistaken for an eval result."""
    report = await run_suite(ScriptedModel({}), [Case(id="a", prompt="x")])
    assert "not a real model" in report.model
    assert "not a real model" in render(report)
