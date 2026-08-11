"""Response playbooks — the layer between a diagnosis and a next step.

`alert_correlator` could tell you an anomaly looked like T1071.001 and stop
there. These tests pin the indexing and lookup that turn that into a procedure,
and — just as important — the behaviour when no corpus is installed, which is
the state every fresh clone starts in.

The fixtures below are written in the same Anthropic-Skills layout the real
corpus uses, so the suite never needs an ~800-file third-party checkout.
"""
from __future__ import annotations

import pytest

from core.playbooks import (
    INSTALL_HINT,
    PlaybookLibrary,
    normalise_technique,
    technique_base,
)

_SKILL = """---
name: {name}
description: {description}
domain: cybersecurity
subdomain: {subdomain}
tags:
{tags}
version: '1.0'
license: Apache-2.0
mitre_attack:
{attack}
nist_csf:
- DE.AE-02
---

# {name}

## When to Use
{description}

## Prerequisites
- A memory image
- Root on the analysis host

## Workflow
1. Acquire the image.
2. Identify the profile.
3. Enumerate processes.

## Verification
Confirm the process list matches the host's expected baseline.
"""


def _write(root, name, *, techniques, description="Do the thing.",
           tags=("forensics",), subdomain="digital-forensics"):
    directory = root / "skills" / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(
        _SKILL.format(
            name=name,
            description=description,
            subdomain=subdomain,
            tags="\n".join(f"- {t}" for t in tags),
            attack="\n".join(f"- {t}" for t in techniques),
        ),
        encoding="utf-8",
    )


@pytest.fixture
def corpus(tmp_path):
    _write(tmp_path, "performing-memory-forensics-with-volatility3",
           techniques=["T1055", "T1003"],
           description="Analyse RAM dumps to recover volatile evidence.",
           tags=("forensics", "memory-forensics", "volatility"))
    _write(tmp_path, "investigating-c2-beaconing",
           techniques=["T1071.001"],
           description="Identify command-and-control beaconing over web protocols.",
           tags=("network", "c2", "beaconing"), subdomain="threat-hunting")
    _write(tmp_path, "hardening-application-layer-protocols",
           techniques=["T1071"],
           description="Reduce exposure of application-layer protocols to C2 abuse.",
           tags=("hardening",), subdomain="defense")
    _write(tmp_path, "containing-ransomware",
           techniques=["T1486"],
           description="Isolate and contain an active ransomware incident.",
           tags=("ransomware", "containment"), subdomain="incident-response")
    return PlaybookLibrary(tmp_path)


# ═══════════════════════════════════════════════════════════════════════════
# Indexing
# ═══════════════════════════════════════════════════════════════════════════


def test_the_corpus_is_indexed(corpus):
    assert corpus.load() == 4
    assert corpus.installed is True


def test_frontmatter_is_read_into_structured_fields(corpus):
    playbook = corpus.get("containing-ransomware")
    assert playbook is not None
    assert playbook.description.startswith("Isolate and contain")
    assert playbook.subdomain == "incident-response"
    assert "ransomware" in playbook.tags
    assert playbook.techniques == ["T1486"]
    assert playbook.frameworks["nist_csf"] == ["DE.AE-02"]
    assert playbook.license == "Apache-2.0"


def test_a_nested_framework_table_is_flattened_to_ids(tmp_path):
    """F3 is a dict — version, tactics, and a techniques table — not a list.

    Stringifying that dict, as a naive reader does, put several hundred
    characters of YAML into the model's context where an id belonged.
    """
    directory = tmp_path / "skills" / "nested-frameworks"
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        "---\n"
        "name: nested-frameworks\n"
        "description: Investigate payment fraud infrastructure.\n"
        "mitre_attack:\n"
        "- T1566\n"
        "mitre_f3:\n"
        "  version: '1.1'\n"
        "  tactics:\n"
        "  - monetization\n"
        "  techniques:\n"
        "  - id: F1020.002\n"
        "    name: 'Create Fake Materials: Fake Website'\n"
        "    source: f3\n"
        "  - id: T1583.001\n"
        "    name: 'Acquire Infrastructure: Domains'\n"
        "    source: attack\n"
        "---\n\n## Workflow\n1. Do the thing.\n",
        encoding="utf-8",
    )
    library = PlaybookLibrary(tmp_path)
    library.load()
    playbook = library.get("nested-frameworks")

    assert playbook.frameworks["f3"] == ["F1020.002"], "ids only, no YAML blob"
    # An ATT&CK id cited inside the F3 table is coverage the corpus already
    # paid for, and belongs in the ATT&CK index rather than the F3 one.
    assert playbook.techniques == ["T1566", "T1583.001"]
    assert library.for_technique("T1583.001")[0].name == "nested-frameworks"


def test_the_repo_root_and_the_skills_dir_both_work(tmp_path):
    """`make playbooks` clones a repo; a user may point at skills/ directly."""
    _write(tmp_path, "a-playbook", techniques=["T1001"])
    assert PlaybookLibrary(tmp_path).load() == 1
    assert PlaybookLibrary(tmp_path / "skills").load() == 1


def test_bodies_are_not_held_in_the_index(corpus):
    """~800 procedures resident to answer 'which mention T1071' is absurd."""
    corpus.load()
    playbook = corpus.get("containing-ransomware")
    assert not hasattr(playbook, "_body")
    assert "Isolate and contain" in playbook.body()


def test_sections_split_on_h2_headings(corpus):
    sections = corpus.get("containing-ransomware").sections()
    assert list(sections) == [
        "When to Use", "Prerequisites", "Workflow", "Verification",
    ]
    assert "Acquire the image." in sections["Workflow"]
    assert "---" not in sections["When to Use"], "frontmatter leaked into the body"


def test_one_malformed_skill_does_not_stop_the_index(tmp_path):
    _write(tmp_path, "good-playbook", techniques=["T1001"])
    broken = tmp_path / "skills" / "broken-playbook"
    broken.mkdir(parents=True)
    (broken / "SKILL.md").write_text("---\nname: [unclosed\n  bracket: yes\n---\nbody")

    library = PlaybookLibrary(tmp_path)
    assert library.load() == 1
    assert library.get("good-playbook") is not None


def test_a_skill_with_no_frontmatter_is_skipped_and_recorded(tmp_path):
    _write(tmp_path, "good-playbook", techniques=["T1001"])
    bare = tmp_path / "skills" / "bare"
    bare.mkdir(parents=True)
    (bare / "SKILL.md").write_text("# just a heading, no frontmatter")

    library = PlaybookLibrary(tmp_path)
    library.load()
    assert library.get("bare") is None
    assert any("bare" in e for e in library.status()["parse_errors"])


# ═══════════════════════════════════════════════════════════════════════════
# Technique lookup — the reason this exists
# ═══════════════════════════════════════════════════════════════════════════


def test_an_exact_technique_match(corpus):
    found = corpus.for_technique("T1486")
    assert [p.name for p in found] == ["containing-ransomware"]


def test_the_playbook_a_technique_is_actually_about_ranks_first(tmp_path):
    """Insertion order is alphabetical by filename, which put broad survey
    playbooks ahead of the one that is actually about the technique.

    A technique listed *first* in a playbook's mapping is that playbook's
    subject rather than an aside; fewer techniques overall means more targeted.
    """
    _write(tmp_path, "a-broad-survey-of-everything",
           techniques=["T1001", "T1002", "T1003", "T1486"])
    _write(tmp_path, "z-containing-ransomware", techniques=["T1486", "T1490"])

    library = PlaybookLibrary(tmp_path)
    names = [p.name for p in library.for_technique("T1486")]
    assert names == ["z-containing-ransomware", "a-broad-survey-of-everything"]


def test_a_sub_technique_alert_finds_the_parent_playbook(corpus):
    """The correlator emits whatever enrichment produced.

    Refusing to show the T1071 procedure for a T1071.001 alert would be
    pedantry at exactly the moment somebody needs an answer.
    """
    names = [p.name for p in corpus.for_technique("T1071.001")]
    assert names[0] == "investigating-c2-beaconing", "exact match must rank first"
    assert "hardening-application-layer-protocols" in names


def test_a_parent_technique_alert_finds_the_sub_technique_playbook(corpus):
    names = [p.name for p in corpus.for_technique("T1071")]
    assert names[0] == "hardening-application-layer-protocols"
    assert "investigating-c2-beaconing" in names


def test_lookup_is_case_insensitive(corpus):
    assert corpus.for_technique("t1486")[0].name == "containing-ransomware"


def test_a_technique_nothing_covers_returns_empty_not_an_error(corpus):
    assert corpus.for_technique("T9999") == []


def test_a_non_technique_string_returns_empty(corpus):
    for junk in ("ransomware", "", "TX", "1071", None):
        assert corpus.for_technique(junk) == []


def test_several_techniques_are_unioned_without_duplicates(corpus):
    found = corpus.for_techniques(["T1071.001", "T1071", "T1486"], limit=10)
    names = [p.name for p in found]
    assert len(names) == len(set(names))
    assert "containing-ransomware" in names
    assert "investigating-c2-beaconing" in names


def test_technique_helpers():
    assert normalise_technique(" t1071.001 ") == "T1071.001"
    assert normalise_technique("T1071") == "T1071"
    assert normalise_technique("nonsense") == ""
    assert normalise_technique(None) == ""
    assert technique_base("T1071.001") == "T1071"
    assert technique_base("T1071") == "T1071"


# ═══════════════════════════════════════════════════════════════════════════
# Search and direct access
# ═══════════════════════════════════════════════════════════════════════════


def test_search_ranks_a_name_match_above_a_description_match(corpus):
    found = corpus.search("ransomware")
    assert found[0].name == "containing-ransomware"


def test_search_covers_tags(corpus):
    assert [p.name for p in corpus.search("volatility")] == [
        "performing-memory-forensics-with-volatility3"
    ]


def test_search_for_nothing_returns_nothing(corpus):
    assert corpus.search("") == []
    assert corpus.search("zzzznomatch") == []


def test_get_tolerates_a_near_miss_slug(corpus):
    """An operator retyping a 45-character slug exactly is not the goal."""
    assert corpus.get("Containing Ransomware").name == "containing-ransomware"
    assert corpus.get("CONTAINING-RANSOMWARE").name == "containing-ransomware"
    assert corpus.get("no-such-playbook") is None


# ═══════════════════════════════════════════════════════════════════════════
# Absent is not broken — the state every fresh clone starts in
# ═══════════════════════════════════════════════════════════════════════════


def test_no_corpus_means_empty_answers_not_exceptions(tmp_path):
    library = PlaybookLibrary(tmp_path / "nothing-here")
    assert library.installed is False
    assert library.load() == 0
    assert library.for_technique("T1071") == []
    assert library.search("ransomware") == []
    assert library.get("anything") is None


def test_status_explains_how_to_install(tmp_path):
    status = PlaybookLibrary(tmp_path / "nothing-here").status()
    assert status["installed"] is False
    assert status["playbooks"] == 0
    assert "make playbooks" in status["hint"]


def test_status_counts_coverage_per_framework(corpus):
    status = corpus.status()
    assert status["installed"] is True
    assert status["playbooks"] == 4
    assert status["techniques_covered"] == 5
    assert status["by_framework"]["attack"] == 4
    assert status["by_framework"]["nist_csf"] == 4
    assert status["by_framework"]["atlas"] == 0


def test_the_directory_is_configurable_by_env(tmp_path, monkeypatch):
    _write(tmp_path, "env-playbook", techniques=["T1001"])
    monkeypatch.setenv("DEEP_PLAYBOOKS_DIR", str(tmp_path))
    assert PlaybookLibrary().load() == 1


# ═══════════════════════════════════════════════════════════════════════════
# Tool surface
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def registry(corpus, monkeypatch):
    import core.playbooks as mod
    from core.tools.deep_registry import DeepToolRegistry

    monkeypatch.setattr(mod, "_shared_library", corpus)
    return DeepToolRegistry()


def test_the_playbook_tools_are_registered():
    from core.tools.registry import TOOL_SPECS

    for name in ("playbook_lookup", "playbook_search", "playbook_read"):
        assert name in TOOL_SPECS


@pytest.mark.asyncio
async def test_lookup_returns_procedures_for_a_technique(registry):
    result = await registry.execute_tool("playbook_lookup", {"technique": "T1071.001"})
    assert result.ok
    assert "investigating-c2-beaconing" in result.content
    assert "attack: T1071.001" in result.content, "the model must be able to cite it"


@pytest.mark.asyncio
async def test_lookup_rejects_a_non_technique_with_the_expected_shape(registry):
    result = await registry.execute_tool("playbook_lookup", {"technique": "ransomware"})
    assert not result.ok
    assert "T1071.001" in result.content


@pytest.mark.asyncio
async def test_read_returns_the_workflow_steps(registry):
    result = await registry.execute_tool(
        "playbook_read", {"name": "containing-ransomware"}
    )
    assert result.ok
    assert "## Workflow" in result.content
    assert "Acquire the image." in result.content


@pytest.mark.asyncio
async def test_read_suggests_near_misses(registry):
    result = await registry.execute_tool("playbook_read", {"name": "ransomware"})
    assert not result.ok
    assert "containing-ransomware" in result.content


@pytest.mark.asyncio
async def test_the_tools_tell_the_model_not_to_invent_steps(monkeypatch, tmp_path):
    """A missing corpus must not become an improvised incident-response plan."""
    import core.playbooks as mod
    from core.tools.deep_registry import DeepToolRegistry

    monkeypatch.setattr(mod, "_shared_library", PlaybookLibrary(tmp_path / "empty"))
    registry = DeepToolRegistry()

    for name, args in [
        ("playbook_lookup", {"technique": "T1071"}),
        ("playbook_search", {"query": "ransomware"}),
        ("playbook_read", {"name": "anything"}),
    ]:
        result = await registry.execute_tool(name, args)
        assert not result.ok, name
        assert "inventing steps" in result.content, name


# ═══════════════════════════════════════════════════════════════════════════
# Terminal and API
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_the_terminal_resolves_a_technique(corpus, monkeypatch):
    import core.playbooks as mod
    from core.intel.ops_terminal import OpsTerminal

    monkeypatch.setattr(mod, "_shared_library", corpus)
    result = await OpsTerminal().execute("playbook T1486")
    assert result.ok
    assert "containing-ransomware" in result.text


@pytest.mark.asyncio
async def test_the_terminal_resolves_a_topic_and_an_exact_name(corpus, monkeypatch):
    import core.playbooks as mod
    from core.intel.ops_terminal import OpsTerminal

    monkeypatch.setattr(mod, "_shared_library", corpus)
    terminal = OpsTerminal()

    topic = await terminal.execute("playbook ransomware")
    assert topic.ok and "containing-ransomware" in topic.text

    exact = await terminal.execute("playbook containing-ransomware")
    assert exact.ok
    assert "## Workflow" in exact.text, "an exact name should print the procedure"


@pytest.mark.asyncio
async def test_the_terminal_says_how_to_install_when_absent(tmp_path, monkeypatch):
    import core.playbooks as mod
    from core.intel.ops_terminal import OpsTerminal

    monkeypatch.setattr(mod, "_shared_library", PlaybookLibrary(tmp_path / "empty"))
    result = await OpsTerminal().execute("playbook T1071")
    assert not result.ok
    assert "make playbooks" in result.error


def test_the_status_endpoint_answers_whether_a_corpus_is_installed(client):
    r = client.get("/api/intel/playbooks/status")
    assert r.status_code == 200
    assert "installed" in r.json()


def test_the_lookup_endpoint_503s_without_a_corpus(client):
    """503 not 200-with-empty-list: 'none installed' differs from 'none match'."""
    from core.playbooks import shared_playbooks

    if shared_playbooks().installed:
        pytest.skip("a playbook corpus is installed in this environment")
    r = client.get("/api/intel/playbooks?technique=T1071")
    assert r.status_code == 503
    assert "make playbooks" in r.json()["detail"]


def test_a_malformed_technique_id_is_422_not_an_empty_result(client):
    """`for_technique` returns [] for a bad id and for a valid-but-uncovered
    one alike, so without a check "T1O71" (letter O) reads as "no procedure
    exists for this" rather than "that is not a technique id"."""
    response = client.get("/api/intel/playbooks?technique=T1O71")
    assert response.status_code in (422, 503)
    if response.status_code == 422:
        assert "T1071" in response.json()["detail"]


def test_the_lookup_endpoint_requires_a_query(client):
    r = client.get("/api/intel/playbooks")
    assert r.status_code in (422, 503)


def test_the_install_hint_names_the_source_and_the_command():
    assert "make playbooks" in INSTALL_HINT
    assert "DEEP_PLAYBOOKS_DIR" in INSTALL_HINT
