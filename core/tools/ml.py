"""
core/tools/ml.py

Machine-learning knowledge tools, migrated from the legacy tool_registry if/elif
to the modern @tool registry. (The heavier ml_train/ml_predict still live in the
legacy switch — they use DeepToolRegistry instance helpers — and migrate later.)
"""

from __future__ import annotations

from typing import Any, Dict

from core.tools.registry import tool
from core.domain.models import ToolResult


@tool("ml_list", "List every ML algorithm Deep knows, grouped by family.", {})
async def ml_list(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    from ai import ml_catalog
    return ToolResult(True, ml_catalog.list_all(), "ml_list")


@tool("ml_explain",
      "Explain one ML algorithm: what it does, when to use it, and the library.",
      {"query": "Algorithm name, e.g. 'xgboost', 'lstm', 'dbscan'"})
async def ml_explain(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    from ai import ml_catalog
    return ToolResult(True, ml_catalog.explain(args.get("query", "")), "ml_explain")


@tool("ml_recommend",
      "Recommend the best ML algorithm(s) for a described problem.",
      {"problem": "e.g. 'detect anomalies in network traffic'"})
async def ml_recommend(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    from ai import ml_catalog
    return ToolResult(True, ml_catalog.recommend(args.get("problem", "")), "ml_recommend")


@tool("ml_runnable", "List which ML algorithms Deep can actually TRAIN/RUN right now.", {})
async def ml_runnable(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    from ai import ml_runner
    return ToolResult(True, "Trainable now: " + ", ".join(ml_runner.runnable_algorithms()), "ml_runnable")
