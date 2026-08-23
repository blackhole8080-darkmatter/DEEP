# Tool-selection evals

DEEP has 66 tools and a language model choosing between them. The pytest suite
proves each tool *works*. Nothing proved the brain *picks the right one* — and
that is the failure that actually degrades a tool-using assistant, the one that
moves every time a tool description is reworded.

```bash
python -m evals.run                                  # ollama:llama3.2 by default
python -m evals.run --model anthropic:claude-sonnet-4-5
python -m evals.run --tag urlscan --verbose
python -m evals.run --json baseline.json --min-accuracy 0.8
```

## What it measures

Five outcomes, kept apart because each has a different fix:

| Outcome | Means | Usually fixed by |
|---|---|---|
| `correct` | expected tool, or a listed alternative | — |
| `wrong_tool` | a real tool, but not this question's | disambiguating two overlapping descriptions |
| `over_trigger` | called a tool when none was needed | a negative instruction in the system prompt |
| `under_trigger` | answered from training data | making the tool's trigger condition explicit |
| `invalid_call` | bad JSON or a hallucinated name | costs a corrective loop, not accuracy |

`arg_accuracy` is scored **only over correct tool calls** — a case expecting no
tool has no arguments to get right, and counting it would flatter a model that
finds the right tool then feeds it nonsense. `fallback_rate` tracks answers that
passed via `also_acceptable` rather than the expected tool: a rising fallback
rate is a description drifting into its neighbour's territory, which a headline
accuracy hides.

## Why it drives the real machinery

Prompts come from `DeepToolRegistry.describe_tools()`, the system prompt from
`AsyncBrain._build_system_prompt()`, and replies are parsed by the brain's own
`_extract_tool_json` and `_parse_tool_call`. Reimplementing any of those would
measure the harness instead of the assistant, and would go stale the moment
someone edited the prompt — the exact change this exists to catch.

It earned that on its first run: `_parse_tool_call` called `tools.list_tools()`,
which `DeepToolRegistry` did not implement, so **every tool call raised
AttributeError and killed the turn**. Every tool passed its own unit tests; the
whole surface was unreachable in the running product.

## Adding a case

Append to `evals/cases.py`. Phrase the prompt the way a person actually types —
lowercase, partial, mid-sentence — because a suite that only passes on
well-formed prompts measures nothing about real use. Always write the
`rationale`: it is printed on failure, and a failing eval whose point nobody
remembers gets deleted rather than fixed.

Negative cases (`expected_tool=None`) matter as much as positive ones. Without
them the suite rewards a model that calls a tool on every turn.

## Notes

- `--min-accuracy` defaults to 0. Establish a baseline before gating on a number.
- Temperature is 0 and the router is bypassed: an eval wants one named model
  reproducibly, not whichever provider failed over this minute.
- Running two models is the cheapest way to separate "the descriptions are
  ambiguous" from "the local model is too small" — identical in a single score,
  completely different fixes.
- `tests/test_evals.py` tests the harness offline with a scripted model. A
  scripted run is labelled `not a real model` so a score can never be mistaken
  for an eval result.
