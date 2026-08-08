"""Response playbooks, exposed to DEEP's LLM.

The rest of the stack gets DEEP to a diagnosis — this anomaly matches
``T1071.001``, that CVE is in KEV. What it could not do is answer the next
question, which is the only one anybody actually asks: *so what do I do?*
These tools give the reasoning brain a procedure to read out rather than an
improvised answer, and — because the corpus names its own frameworks — one that
can be cited back to ATT&CK or NIST CSF instead of being taken on faith.

Output is deliberately trimmed. A full playbook body runs to several KB and the
result is re-fed to the model; the lookup returns descriptions, and only a
directly-named playbook returns its workflow.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.domain.models import ToolResult
from core.playbooks import Playbook, normalise_technique, shared_playbooks
from core.tools.registry import tool

#: Preference order for sections, not an allowlist — corpora vary in their
#: heading vocabulary ("Verification" vs "Validation Criteria"), and dropping a
#: procedure's only workflow section because it was named unexpectedly would be
#: worse than spending a few hundred extra tokens.
_SECTION_ORDER = (
    "When to Use", "Overview", "Prerequisites", "Workflow", "Validation Criteria",
    "Verification", "Common Scenarios", "Common Pitfalls", "Tools & Systems",
    "Output Format",
)

#: Budget for a rendered playbook's header and sections; the framework citation
#: footer is appended after it. Results are re-fed to the model, and the longest
#: procedures in the reference corpus run past 20 KB.
_MAX_BODY_CHARS = 6000


def _summarise(playbooks: List[Playbook]) -> str:
    lines = []
    for p in playbooks:
        frameworks = ", ".join(
            f"{name}: {', '.join(ids[:4])}"
            for name, ids in sorted(p.frameworks.items())
        )
        lines.append(f"- {p.name}\n  {p.description[:240]}")
        if frameworks:
            lines.append(f"  [{frameworks}]")
    return "\n".join(lines)


def _not_installed(tool_name: str) -> ToolResult:
    return ToolResult(
        False,
        "No response playbooks are installed on this system, so there is no "
        "procedure to quote. Say so rather than inventing steps.",
        tool_name,
    )


@tool(
    "playbook_lookup",
    "Find the response procedures that cover a MITRE ATT&CK technique. Use this "
    "whenever an alert, anomaly or timeline entry names a technique (T1071, "
    "T1566.001) and the user asks what to do, how to investigate, how to "
    "respond, or how to contain it. Returns real procedures from an installed "
    "playbook corpus — quote those steps rather than improvising a response "
    "plan, and name the playbook you used.",
    {"technique": "MITRE ATT&CK technique id, e.g. T1071 or T1071.001"},
)
async def playbook_lookup(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    raw = str(args.get("technique", "")).strip()
    if not raw:
        return ToolResult(False, "Missing technique.", "playbook_lookup")

    technique = normalise_technique(raw)
    if not technique:
        return ToolResult(
            False,
            f"'{raw}' is not an ATT&CK technique id. Expected TNNNN or TNNNN.NNN "
            "(for example T1071 or T1071.001).",
            "playbook_lookup",
        )

    library = shared_playbooks()
    if not library.installed:
        return _not_installed("playbook_lookup")

    found = library.for_technique(technique, limit=5)
    if not found:
        return ToolResult(
            True,
            f"No installed playbook covers {technique}. "
            f"The corpus indexes {library.status()['techniques_covered']} techniques.",
            "playbook_lookup",
        )
    return ToolResult(
        True,
        f"{len(found)} playbook(s) covering {technique}:\n{_summarise(found)}\n\n"
        "Call playbook_read with a name for its full workflow.",
        "playbook_lookup",
    )


@tool(
    "playbook_search",
    "Search response playbooks by topic when no ATT&CK technique is in hand — "
    "'memory forensics', 'phishing', 'ransomware containment', 'log4j'. Use it "
    "before answering any 'how do I investigate/respond to X' question, so the "
    "answer follows an established procedure instead of being improvised.",
    {"query": "topic, tool or threat, e.g. 'memory forensics' or 'ransomware'"},
)
async def playbook_search(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    query = str(args.get("query", "")).strip()
    if not query:
        return ToolResult(False, "Missing query.", "playbook_search")

    library = shared_playbooks()
    if not library.installed:
        return _not_installed("playbook_search")

    found = library.search(query, limit=8)
    if not found:
        return ToolResult(True, f"No playbook matches '{query}'.", "playbook_search")
    return ToolResult(
        True,
        f"{len(found)} playbook(s) matching '{query}':\n{_summarise(found)}\n\n"
        "Call playbook_read with a name for its full workflow.",
        "playbook_search",
    )


@tool(
    "playbook_read",
    "Read one playbook's actual procedure — prerequisites, workflow steps and "
    "verification. Use after playbook_lookup or playbook_search has given you a "
    "name, and follow the steps as written rather than paraphrasing them into "
    "something vaguer.",
    {"name": "playbook name from playbook_lookup or playbook_search"},
)
async def playbook_read(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    name = str(args.get("name", "")).strip()
    if not name:
        return ToolResult(False, "Missing name.", "playbook_read")

    library = shared_playbooks()
    if not library.installed:
        return _not_installed("playbook_read")

    playbook = library.get(name)
    if playbook is None:
        near = library.search(name, limit=3)
        hint = f" Closest matches: {', '.join(p.name for p in near)}." if near else ""
        return ToolResult(False, f"No playbook named '{name}'.{hint}", "playbook_read")

    sections = playbook.sections()
    ordered = [h for h in _SECTION_ORDER if h in sections]
    ordered += [h for h in sections if h not in _SECTION_ORDER]

    header = f"{playbook.name}\n{playbook.description}"
    parts = [header]
    budget = _MAX_BODY_CHARS - len(header)
    for index, heading in enumerate(ordered):
        prefix = f"\n## {heading}\n"
        if budget <= len(prefix):
            parts.append(
                f"\n(sections omitted for length: {', '.join(ordered[index:])})"
            )
            break
        block = prefix + sections[heading][: budget - len(prefix)]
        budget -= len(block)
        parts.append(block)

    if playbook.frameworks:
        cited = ", ".join(
            f"{k}: {', '.join(v)}" for k, v in sorted(playbook.frameworks.items())
        )
        parts.append(f"\nMapped to — {cited}")
    return ToolResult(True, "\n".join(parts), "playbook_read")
