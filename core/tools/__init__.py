"""DEEP tool registry package.

Importing this package registers every tool. That has to happen here, at
import time, because `@tool` populates `TOOL_SPECS` as a side effect of the
decorator running — and nothing was importing these modules, so the registry
was empty in the live server. `describe_tools()` returned a header and a
format instruction with no tools between them, meaning DEEP's system prompt
promised the LLM tools it was never actually given.

**Order matters.** `legacy` registers its remaining tools in a loop that skips
any name already present:

    for name, info in LEGACY_TOOLS.items():
        if name in TOOL_SPECS:
            continue  # already ported

so it must be imported last, or its generic shims would shadow the migrated
implementations. This is the strangler pattern the registry docstring
describes: tools move out of `legacy` one at a time, and the modern module
silently wins the moment a name appears there.
"""

# ruff: noqa: I001
#   Import order here is load-bearing, not stylistic — see the docstring above.
#   Sorting this block alphabetically would move `legacy` ahead of the migrated
#   modules and silently hand every ported tool name back to its generic shim.

from core.tools.registry import TOOL_SPECS, ToolSpec, tool  # noqa: F401

# Modern, migrated tools first.
from core.tools import builtin as _builtin  # noqa: F401,E402
from core.tools import files as _files  # noqa: F401,E402
from core.tools import intel as _intel  # noqa: F401,E402
from core.tools import local_estate as _local_estate  # noqa: F401,E402
from core.tools import ml as _ml  # noqa: F401,E402
from core.tools import etis as _etis  # noqa: F401,E402
from core.tools import playbooks as _playbooks  # noqa: F401,E402

# Legacy shims last — see the note above.
from core.tools import legacy as _legacy  # noqa: F401,E402

__all__ = ["TOOL_SPECS", "ToolSpec", "tool"]
