"""
core/integrations/local_system.py

Local System & Code Intelligence for Deep.

Replaces the dummy `integration_manager.get("local_system")` (which returned
None, silently breaking every file/command tool) with a real, sandboxed
implementation — and adds the code-intelligence tools an agent needs to work
on real codebases the way a human engineer (or Claude Code) does:

  - read_file      : read a file, optionally a line range
  - write_file     : create/overwrite a file (use for NEW files)
  - edit_file      : SURGICAL find/replace in an existing file (no clobbering)
  - list_directory : list a directory
  - glob_files     : find files by glob pattern (e.g. **/*.py)
  - search_code    : grep across the codebase (ripgrep if available, else pure-Python)
  - run_command    : run a shell command with a timeout

Everything is sandboxed to a workspace root (env DEEP_WORKSPACE_ROOT, default
the user's home directory). Paths that escape the root are rejected.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# Directories that are noise for code search / globbing — skip them.
_SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".mypy_cache",
    ".pytest_cache", ".idea", ".vscode", "dist", "build", ".next", "target",
}
_BINARY_HINT_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".tar",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".pyc", ".onnx", ".pt", ".wav",
    ".mp3", ".mp4", ".db", ".sqlite",
}

MAX_READ_BYTES = 1_000_000  # 1 MB safety cap per read


class WorkspaceSecurityError(Exception):
    """Raised when a path escapes the sandbox root."""


class LocalSystem:
    """Sandboxed filesystem + command access for Deep's coding/automation tools."""

    def __init__(self, root: Optional[str] = None):
        # Default to the project area (parent of the DEEP dir), NOT the whole home
        # directory: home is enormous (AppData etc.), making code search crawl, and a
        # narrower sandbox is safer. Override with DEEP_WORKSPACE_ROOT.
        default_root = Path(__file__).resolve().parents[3]  # .../Aryan_Private
        chosen = root or os.getenv("DEEP_WORKSPACE_ROOT") or str(default_root)
        self.root = Path(chosen).expanduser().resolve()
        logger.info(f"[LocalSystem] Workspace root: {self.root}")

    # ─── Path safety ──────────────────────────────────────────────────────────

    def _resolve(self, path: str) -> Path:
        """Resolve a path (absolute or relative-to-root) and ensure it stays inside root."""
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = self.root / p
        p = p.resolve()
        if p != self.root and self.root not in p.parents:
            raise WorkspaceSecurityError(
                f"Path '{path}' escapes the workspace sandbox ({self.root})."
            )
        return p

    # ─── Files ────────────────────────────────────────────────────────────────

    async def read_file(self, filepath: str, start: Optional[int] = None,
                        end: Optional[int] = None) -> str:
        p = self._resolve(filepath)
        if not p.exists():
            return f"ERROR: file not found: {filepath}"
        if p.is_dir():
            return f"ERROR: {filepath} is a directory (use list_directory)."
        if p.stat().st_size > MAX_READ_BYTES:
            return f"ERROR: file too large (> {MAX_READ_BYTES} bytes)."
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"ERROR reading file: {e}"
        if start is None and end is None:
            return text
        lines = text.splitlines()
        s = max(0, (start or 1) - 1)
        e = end or len(lines)
        chosen = lines[s:e]
        return "\n".join(f"{s + i + 1}\t{ln}" for i, ln in enumerate(chosen))

    async def write_file(self, filepath: str, content: str) -> str:
        p = self._resolve(filepath)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            existed = p.exists()
            p.write_text(content, encoding="utf-8")
            verb = "Overwrote" if existed else "Created"
            return f"{verb} {filepath} ({len(content)} bytes)."
        except Exception as e:
            return f"ERROR writing file: {e}"

    async def edit_file(self, filepath: str, old: str, new: str,
                        replace_all: bool = False) -> str:
        """Surgical find/replace — the safe way to edit existing code."""
        p = self._resolve(filepath)
        if not p.exists():
            return f"ERROR: file not found: {filepath}"
        try:
            text = p.read_text(encoding="utf-8")
        except Exception as e:
            return f"ERROR reading file: {e}"
        if old == new:
            return "ERROR: old and new text are identical."
        count = text.count(old)
        if count == 0:
            return ("ERROR: old text not found. It must match the file EXACTLY "
                    "(including whitespace). Read the file first.")
        if count > 1 and not replace_all:
            return (f"ERROR: old text appears {count} times (not unique). "
                    "Add surrounding context to make it unique, or set replace_all=true.")
        new_text = text.replace(old, new) if replace_all else text.replace(old, new, 1)
        try:
            p.write_text(new_text, encoding="utf-8")
        except Exception as e:
            return f"ERROR writing file: {e}"
        n = count if replace_all else 1
        return f"Edited {filepath} ({n} replacement{'s' if n != 1 else ''})."

    async def list_directory(self, path: str = ".") -> str:
        p = self._resolve(path)
        if not p.exists():
            return f"ERROR: directory not found: {path}"
        if not p.is_dir():
            return f"ERROR: {path} is a file, not a directory."
        entries = []
        for child in sorted(p.iterdir(), key=lambda c: (c.is_file(), c.name.lower())):
            kind = "dir " if child.is_dir() else "file"
            entries.append(f"[{kind}] {child.name}")
        return "\n".join(entries) if entries else "(empty directory)"

    # ─── Code intelligence ──────────────────────────────────────────────────────

    async def glob_files(self, pattern: str, path: Optional[str] = None,
                         limit: int = 200) -> str:
        base = self._resolve(path) if path else self.root
        if not base.is_dir():
            return f"ERROR: {path or base} is not a directory."

        def _glob() -> List[str]:
            out = []
            for f in base.rglob(pattern):
                if any(part in _SKIP_DIRS for part in f.parts):
                    continue
                if f.is_file():
                    out.append(str(f.relative_to(self.root)))
                    if len(out) >= limit:
                        break
            return out

        matches = await asyncio.to_thread(_glob)
        if not matches:
            return f"No files matching '{pattern}'."
        head = f"{len(matches)} match(es)" + (" (capped)" if len(matches) >= limit else "") + ":\n"
        return head + "\n".join(matches)

    async def search_code(self, query: str, path: Optional[str] = None,
                         glob: Optional[str] = None, max_results: int = 80) -> str:
        """Grep across files. Uses ripgrep if installed; falls back to pure-Python."""
        base = self._resolve(path) if path else self.root
        rg = shutil.which("rg")
        if rg:
            return await self._search_ripgrep(rg, query, base, glob, max_results)
        return await self._search_python(query, base, glob, max_results)

    async def _search_ripgrep(self, rg: str, query: str, base: Path,
                             glob: Optional[str], max_results: int) -> str:
        args = [rg, "--line-number", "--no-heading", "--color", "never",
                "-m", str(max_results), query, str(base)]
        if glob:
            args[1:1] = ["--glob", glob]
        try:
            proc = await asyncio.create_subprocess_exec(
                *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        except asyncio.TimeoutError:
            return "ERROR: search timed out."
        except Exception as e:
            return f"ERROR running ripgrep: {e}"
        text = out.decode("utf-8", errors="replace").strip()
        if not text:
            return f"No matches for '{query}'."
        lines = text.splitlines()[:max_results]
        # Make paths relative to root for readability
        rel = []
        for ln in lines:
            rel.append(ln.replace(str(base) + os.sep, "").replace(str(self.root) + os.sep, ""))
        return f"{len(rel)} match(es):\n" + "\n".join(rel)

    async def _search_python(self, query: str, base: Path,
                            glob: Optional[str], max_results: int) -> str:
        def _scan() -> List[str]:
            results = []
            q = query.lower()
            pattern = glob or "*"
            for f in base.rglob(pattern):
                if not f.is_file():
                    continue
                if any(part in _SKIP_DIRS for part in f.parts):
                    continue
                if f.suffix.lower() in _BINARY_HINT_EXT:
                    continue
                try:
                    if f.stat().st_size > MAX_READ_BYTES:
                        continue
                    for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                        if q in line.lower():
                            rel = f.relative_to(self.root)
                            results.append(f"{rel}:{i}: {line.strip()[:200]}")
                            if len(results) >= max_results:
                                return results
                except Exception:
                    continue
            return results

        results = await asyncio.to_thread(_scan)
        if not results:
            return f"No matches for '{query}'."
        return f"{len(results)} match(es):\n" + "\n".join(results)

    # ─── Commands ────────────────────────────────────────────────────────────────

    async def run_command(self, command: str, cwd: Optional[str] = None,
                         timeout: int = 60) -> dict:
        work_dir = self._resolve(cwd) if cwd else self.root
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_dir),
            )
            try:
                out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                return {"exit_code": -1, "stdout": "", "stderr": f"Command timed out after {timeout}s."}
            return {
                "exit_code": proc.returncode,
                "stdout": out.decode("utf-8", errors="replace")[-8000:],
                "stderr": err.decode("utf-8", errors="replace")[-4000:],
            }
        except Exception as e:
            return {"exit_code": -1, "stdout": "", "stderr": f"Failed to run command: {e}"}
