"""The fixture set: what DEEP should reach for, and when.

Two kinds of case, and the second matters as much as the first:

* **Positive** — a prompt that should produce a specific tool call. Catches a
  tool the model cannot find, usually because its description is written for a
  human skimming a list rather than a model matching intent.
* **Negative** (`expected_tool=None`) — a prompt that should be answered
  directly. Catches over-triggering, which is the more insidious failure: a
  model that calls `threat_lookup` on "what's a CVE?" is slow, burns rate
  limit, and looks broken in a way no unit test notices.

Cases are deliberately phrased the way a person actually types — lowercase,
partial, occasionally rude — rather than as clean specifications. A suite that
only passes on well-formed prompts measures nothing about real use.

`expected_args` are matched as case-insensitive substrings of the stringified
argument values, not exact equality: the interesting question is whether the
model pulled the right *indicator* out of the sentence, not whether it
normalised the trailing slash the same way you would.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True, slots=True)
class Case:
    """One prompt and what DEEP ought to do with it."""

    id: str
    prompt: str
    #: Tool that should be called, or None when the turn needs no tool at all.
    expected_tool: Optional[str] = None
    #: Substrings that must appear in the call's arguments.
    expected_args: Dict[str, str] = field(default_factory=dict)
    #: Other tools that are a defensible answer. Scored as a pass, counted
    #: separately, because "acceptable" and "what I meant" are not the same and
    #: collapsing them hides a description that is drifting.
    also_acceptable: tuple[str, ...] = ()
    #: Free-text note on why this case exists. Shown on failure — a failing
    #: eval whose point nobody remembers gets deleted rather than fixed.
    rationale: str = ""
    tags: tuple[str, ...] = ()


CASES: List[Case] = [
    # ── URLs: the indicator DEEP could not investigate until recently ────────
    Case(
        id="url.pasted_link",
        prompt="is https://secure-login.paypa1-verify.top/session safe?",
        expected_tool="url_lookup",
        expected_args={"url": "paypa1-verify.top"},
        also_acceptable=("threat_lookup",),
        rationale="The headline case for the urlscan work. A pasted link is the "
                  "single most common way a person brings DEEP a security question.",
        tags=("urlscan", "security"),
    ),
    Case(
        id="url.forwarded_email",
        prompt="my bank emailed me a link, http://account-verify.icu/login?id=99 — legit?",
        expected_tool="url_lookup",
        expected_args={"url": "account-verify.icu"},
        also_acceptable=("threat_lookup",),
        rationale="Phrased as a person actually forwards a phish: context first, "
                  "URL buried mid-sentence, question at the end.",
        tags=("urlscan", "security"),
    ),
    Case(
        id="url.host_not_page",
        prompt="check this link for me https://sites.google.com/view/free-gift-card-2026",
        expected_tool="url_lookup",
        expected_args={"url": "sites.google.com/view/free-gift-card"},
        rationale="A reputable host serving an abusive path. If the model reaches "
                  "for the domain tool it answers about google.com, which is the "
                  "exact confusion url_lookup exists to prevent.",
        tags=("urlscan", "security"),
    ),
    Case(
        id="url.submit_needs_scanning",
        prompt="nobody has scanned https://brand-new-domain.test/ yet — run a live scan of it",
        expected_tool="url_scan_submit",
        expected_args={"url": "brand-new-domain.test"},
        rationale="Explicitly asks for a *live* scan. Reaching for url_lookup here "
                  "would silently answer a different question from the one asked.",
        tags=("urlscan",),
    ),

    # ── Other indicators ─────────────────────────────────────────────────────
    Case(
        id="ip.reputation",
        prompt="is 45.33.32.156 malicious",
        expected_tool="threat_lookup",
        expected_args={"target": "45.33.32.156"},
        also_acceptable=("investigate", "etis_reputation_check"),
        tags=("intel", "security"),
    ),
    Case(
        id="cve.urgency",
        prompt="how urgent is CVE-2021-44228 really",
        expected_tool="cve_intel",
        expected_args={"cve_id": "CVE-2021-44228"},
        also_acceptable=("threat_lookup", "etis_cve_lookup"),
        rationale="cve_intel and threat_lookup overlap by design. Both are fine; "
                  "answering from training data is not, since KEV and EPSS move daily.",
        tags=("intel",),
    ),
    Case(
        id="package.audit",
        prompt="does pypi:requests have any known vulns",
        expected_tool="dependency_audit",
        expected_args={"package": "requests"},
        also_acceptable=("threat_lookup",),
        tags=("intel",),
    ),
    Case(
        id="hash.pivot",
        prompt="what else serves this file "
               "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        expected_tool="threat_lookup",
        expected_args={"target": "e3b0c44298fc1c14"},
        also_acceptable=("url_lookup",),
        rationale="Exercises the keyless SHA-256 pivot urlscan added.",
        tags=("urlscan", "intel"),
    ),

    # ── DEEP's own observations, not the internet ────────────────────────────
    Case(
        id="local.devices",
        prompt="what's on my network right now",
        expected_tool="local_devices",
        also_acceptable=("network_scan", "cyber_scan_network"),
        rationale="'my network' must route to DEEP's own observations rather than "
                  "a public lookup — the distinction the local_estate tools exist for.",
        tags=("local",),
    ),
    Case(
        id="local.security_timeline",
        prompt="anything suspicious happen today?",
        expected_tool="security_events",
        also_acceptable=("anomalies", "threat_predictions", "local_devices"),
        tags=("local",),
    ),
    Case(
        id="local.wifi",
        prompt="are there any evil twin access points around me",
        expected_tool="wifi_environment",
        tags=("local",),
    ),
    Case(
        id="local.stack_exposure",
        prompt="any new cves affecting the stuff i actually use?",
        expected_tool="stack_exposure",
        also_acceptable=("threat_landscape",),
        tags=("local", "intel"),
    ),

    # ── Capability questions ─────────────────────────────────────────────────
    Case(
        id="meta.sources",
        prompt="what threat intel sources can you actually query?",
        expected_tool="intel_sources",
        rationale="Should be answered from the live catalog, since which sources "
                  "are configured changes with the environment.",
        tags=("meta",),
    ),
    Case(
        id="meta.time",
        prompt="what time is it",
        expected_tool="get_time",
        rationale="Trivial, and exactly the sort of thing a model answers wrongly "
                  "from its training data if the tool is not obvious enough.",
        tags=("meta",),
    ),

    # ── Negative cases: answering directly is the right move ─────────────────
    Case(
        id="neg.concept_question",
        prompt="what does CVSS actually measure?",
        expected_tool=None,
        rationale="A definition, not a lookup. Calling cve_intel with no CVE is "
                  "the classic over-trigger — it wastes a loop and returns nothing.",
        tags=("negative",),
    ),
    Case(
        id="neg.greeting",
        prompt="hey deep, you there?",
        expected_tool=None,
        tags=("negative",),
    ),
    Case(
        id="neg.opinion",
        prompt="do you think self-hosting email is worth the hassle these days?",
        expected_tool=None,
        rationale="Opinion, no indicator anywhere in it. A model that reaches for "
                  "search_web here will do it for every conversational turn.",
        tags=("negative",),
    ),
    Case(
        id="neg.explain_own_answer",
        prompt="you said the domain was young — why does that matter for phishing?",
        expected_tool=None,
        rationale="A follow-up about reasoning already given. Re-running the lookup "
                  "is the failure where DEEP loops instead of explaining itself.",
        tags=("negative", "urlscan"),
    ),
    Case(
        id="neg.arithmetic",
        prompt="if a scan takes 30 seconds how many can i do in an hour",
        expected_tool=None,
        tags=("negative",),
    ),

    # ── Destructive / outward-facing: the gate should still be reached ───────
    Case(
        id="gate.block_device",
        prompt="block the device at a4:83:e7:2c:11:09, i don't recognise it",
        expected_tool="block_device",
        expected_args={"mac": "a4:83:e7:2c:11:09"},
        rationale="Should reach the tool, which then parks it for approval. The "
                  "eval measures selection; the gate is tested in "
                  "tests/test_action_approvals.py.",
        tags=("gate",),
    ),
]


def by_tag(*tags: str) -> List[Case]:
    """Cases carrying any of these tags."""
    wanted = {t.lower() for t in tags}
    return [c for c in CASES if wanted & {t.lower() for t in c.tags}]
