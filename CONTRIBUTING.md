# Contributing to DEEP

DEEP is a solo, actively-evolving project — contributions are welcome, but
please open an issue before a large PR so we're aligned on direction first.
Small fixes (bugs, docs, tests) can just be a PR directly.

## Setup

```bash
git clone https://github.com/blackhole8080-darkmatter/DEEP.git
cd DEEP
make install
cp .env.example .env
make start
```

See the [README](README.md) for the full picture of what's running and why.

## Conventions this codebase actually follows

- **Graceful degradation over hard failures.** Optional dependencies (nmap,
  scapy, bleak, redis, aiosqlite...) are wrapped in `try/except ImportError`
  and the affected subsystem falls back to a reduced mode with a log line —
  it never crashes the whole app. New optional integrations should follow
  the same pattern.
- **Archive, don't delete.** Retiring a subsystem means `git mv` into
  `archive/`, not `rm`. History and the option to revive it stay intact.
- **Frontend additions are one registry entry.** To add a new panel to the
  HUD: build the Lit component under `interface/web/src/components/`, then
  append one entry to `TOOL_REGISTRY` in
  `interface/web/src/core/tool-registry.ts`. That's the whole integration —
  no routing/layout changes needed.
- **Tests are expected for behavior changes**, not just for new files.
  `pytest` should stay green — run `make test` before opening a PR. If you
  find a test relying on a live network call or an external API, prefer
  mocking at the same seam the existing tests use (see `tests/test_intel_feeds_extended.py`
  for the pattern: mock `_get_json`/`_get_text`/`_post_json`, not `aiohttp` directly).
- **Rebuild the frontend before committing UI changes.** `cd interface/web
  && npm run build` — the compiled output in `interface/static/app-dist` is
  what the backend actually serves, and it's committed (no separate CI build
  step exists yet).

## Reporting bugs / requesting features

Open a GitHub issue. For bugs, include: what you ran, what you expected,
what actually happened, and relevant log output. DEEP touches your local
network and system — please don't include real IPs, MACs, or credentials in
a public issue.

## Security

If you find a real vulnerability in DEEP itself (not in a third-party
dependency), please open an issue and mark it clearly rather than a PR that
discloses it publicly, so it can be addressed before details are public.
