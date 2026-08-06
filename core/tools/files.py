"""
core/tools/files.py

File + code-intelligence tools, migrated to the @tool registry. Handlers use the
sandboxed LocalSystem via `ctx.local_system` (the DeepToolRegistry instance).
"""

from __future__ import annotations

import os
from typing import Any, Dict

from core.tools.registry import tool
from core.domain.models import ToolResult


def _as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


@tool("read_file",
      "Read a file. Optionally pass start/end line numbers to read a range (returns numbered lines).",
      {"filepath": "Path to the file (absolute or relative to workspace)",
       "start": "Optional 1-based start line", "end": "Optional end line"})
async def read_file(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    content = await ctx.local_system.read_file(
        args.get("filepath", ""), _as_int(args.get("start")), _as_int(args.get("end")))
    return ToolResult(not content.startswith("ERROR"), content, "read_file")


@tool("write_file",
      "Create or fully overwrite a file. Use for NEW files; for editing existing code use edit_file instead.",
      {"filepath": "Path to the file", "content": "The full text to write"})
async def write_file(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    res = await ctx.local_system.write_file(args.get("filepath", ""), args.get("content", ""))
    return ToolResult(not res.startswith("ERROR"), res, "write_file")


@tool("edit_file",
      "Surgically edit an existing file via exact find/replace (no clobbering). 'old' must match the file exactly and be unique unless replace_all is true.",
      {"filepath": "Path to the file", "old": "Exact text to replace",
       "new": "Replacement text", "replace_all": "Optional bool, replace every occurrence"})
async def edit_file(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    replace_all = args.get("replace_all") in (True, "true", "True", "1", 1)
    res = await ctx.local_system.edit_file(
        args.get("filepath", ""), args.get("old", ""), args.get("new", ""), replace_all)
    return ToolResult(not res.startswith("ERROR"), res, "edit_file")


@tool("list_directory", "List all files and folders in a directory.",
      {"path": "Path to the directory (absolute or relative to workspace)"})
async def list_directory(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    res = await ctx.local_system.list_directory(args.get("path", "."))
    return ToolResult(not res.startswith("ERROR"), str(res), "list_directory")


@tool("glob_files",
      "Find files by glob pattern (e.g. '**/*.py') under the workspace or a given path.",
      {"pattern": "Glob pattern, e.g. **/*.py", "path": "Optional base directory"})
async def glob_files(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    res = await ctx.local_system.glob_files(args.get("pattern", "*"), args.get("path"))
    return ToolResult(not res.startswith("ERROR"), res, "glob_files")


@tool("search_code",
      "Search file contents across the codebase (grep). Returns file:line: matches. Use this to FIND code before reading/editing.",
      {"query": "Text/regex to search for", "path": "Optional base directory",
       "glob": "Optional file filter, e.g. *.py"})
async def search_code(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    res = await ctx.local_system.search_code(args.get("query", ""), args.get("path"), args.get("glob"))
    return ToolResult(not res.startswith("ERROR"), res, "search_code")


# run_command is deliberately NOT registered by default.
#
# Every other tool in this module is path-sandboxed — LocalSystem._resolve()
# raises WorkspaceSecurityError for anything outside the workspace root. That
# guarantee does not extend to run_command: it sandboxes the working directory
# but the command string itself is unrestricted, so it is arbitrary shell
# execution under whatever account runs DEEP. Handing that to an LLM by default
# is not a defensible posture for a security tool, so it is opt-in.
if os.environ.get("DEEP_ENABLE_SHELL_TOOL", "").strip().lower() in {"1", "true", "yes", "on"}:
    @tool("run_command",
          "Execute a terminal command on the local machine (e.g. python script.py). Use cautiously.",
          {"command": "The terminal command to run"})
    async def run_command(ctx: Any, args: Dict[str, Any]) -> ToolResult:
        res = await ctx.local_system.run_command(args.get("command", ""))
        output = f"Exit code: {res['exit_code']}\nSTDOUT:\n{res['stdout']}\nSTDERR:\n{res['stderr']}"
        return ToolResult(res["exit_code"] == 0, output, "run_command")
