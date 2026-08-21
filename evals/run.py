"""CLI: python -m evals.run [--model ollama:llama3.2] [--tag urlscan] [--json out.json]

Exits non-zero when accuracy falls below `--min-accuracy`, so this can gate a
commit or a CI job. The default threshold is 0 — a first run should establish a
baseline, not fail against a number nobody has justified yet.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from evals import cases as case_module
from evals.harness import render, run_suite, to_json
from evals.models import AnthropicModel, OllamaModel


def _build_model(spec: str):
    """`ollama:llama3.2`, `anthropic:claude-sonnet-4-5`, or a bare ollama model."""
    provider, _, name = spec.partition(":")
    provider = provider.lower()
    if provider == "anthropic":
        return AnthropicModel(name or "claude-sonnet-4-5")
    if provider == "ollama":
        return OllamaModel(name or "llama3.2")
    return OllamaModel(spec)


async def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="evals.run", description=__doc__)
    parser.add_argument("--model", default="ollama:llama3.2",
                        help="ollama:MODEL or anthropic:MODEL (default: ollama:llama3.2)")
    parser.add_argument("--tag", action="append", default=[],
                        help="only cases with this tag; repeatable")
    parser.add_argument("--case", action="append", default=[], help="run one case by id")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--json", type=Path, help="write the full report here")
    parser.add_argument("--min-accuracy", type=float, default=0.0,
                        help="exit non-zero below this tool accuracy (0-1)")
    parser.add_argument("--verbose", action="store_true", help="show raw replies on failure")
    args = parser.parse_args(argv)

    selected = list(case_module.CASES)
    if args.tag:
        selected = case_module.by_tag(*args.tag)
    if args.case:
        wanted = set(args.case)
        selected = [c for c in selected if c.id in wanted]
    if not selected:
        print("No cases matched.", file=sys.stderr)
        return 2

    model = _build_model(args.model)
    # Ask before running rather than after 20 timeouts: a model that is not
    # there should be one clear line, not a slow pile of invalid_call.
    check = getattr(model, "available", None)
    if check is not None:
        reason = await check()
        if reason:
            print(f"Cannot run against {model.name}: {reason}", file=sys.stderr)
            return 2

    done = 0

    def progress(_result) -> None:
        nonlocal done
        done += 1
        print(f"\r  {done}/{len(selected)}", end="", file=sys.stderr, flush=True)

    report = await run_suite(model, selected, concurrency=args.concurrency, on_result=progress)
    print("\r", end="", file=sys.stderr)
    print(render(report, verbose=args.verbose))

    if args.json:
        args.json.write_text(to_json(report), encoding="utf-8")
        print(f"\nwrote {args.json}")

    if report.tool_accuracy < args.min_accuracy:
        print(f"\nFAIL: tool accuracy {report.tool_accuracy:.0%} "
              f"below threshold {args.min_accuracy:.0%}", file=sys.stderr)
        return 1
    return 0


def main() -> None:
    sys.exit(asyncio.run(_main(sys.argv[1:])))


if __name__ == "__main__":
    main()
