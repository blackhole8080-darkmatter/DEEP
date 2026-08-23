"""Tool-selection evals for DEEP.

DEEP has 66 tools and a language model choosing between them. Its unit tests
prove each tool *works*; nothing proved the brain *picks the right one*, which
is the failure that actually degrades a tool-using assistant — and the one that
moves every time a tool description is reworded.

The harness runs a fixture set of prompts through the real prompt builder and
the real tool-call parser, then scores what came back. See `evals/README.md`.
"""

from evals.cases import CASES, Case
from evals.harness import CaseResult, Report, run_case, run_suite

__all__ = ["CASES", "Case", "CaseResult", "Report", "run_case", "run_suite"]
