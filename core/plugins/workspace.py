"""
core/plugins/workspace.py

DEEP Project Workspace Plugin.

Monitors your project directories, tracks git activity,
and feeds code context into the knowledge graph.

Features:
- Watchdog-based file monitoring on ~/Projects (or configured dirs)
- Git branch/commit tracking
- Auto-ingests code files into knowledge graph
- Detects active project based on recent file changes
- Project stats: files changed, last commit, branch
- All local, no API keys

Usage:
    # Auto-discovered by PluginManager on startup
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from core.plugins.base import DeepPlugin

logger = logging.getLogger(__name__)

# Try to import optional deps
_WATCHDOG_AVAILABLE = False
_GIT_AVAILABLE = False

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
    _WATCHDOG_AVAILABLE = True
except ImportError:
    logger.warning("[Workspace] watchdog not installed. File monitoring disabled.")
    Observer = None
    FileSystemEventHandler = object
    FileModifiedEvent = None
    FileCreatedEvent = None

try:
    import git
    _GIT_AVAILABLE = True
except ImportError:
    logger.warning("[Workspace] gitpython not installed. Git tracking disabled.")
    git = None


class WorkspaceEventHandler(FileSystemEventHandler if _WATCHDOG_AVAILABLE else object):
    """Handles file system events for workspace monitoring."""
    
    def __init__(self, plugin: WorkspacePlugin):
        super().__init__()
        self.plugin = plugin
        self._last_event_time = 0
        self._debounce_seconds = 2
    
    def on_modified(self, event):
        if event.is_directory:
            return
        if not self._should_process(event.src_path):
            return
        self._debounced_process(event.src_path, "modified")
    
    def on_created(self, event):
        if event.is_directory:
            return
        if not self._should_process(event.src_path):
            return
        self._debounced_process(event.src_path, "created")
    
    def _should_process(self, path: str) -> bool:
        # Skip hidden files, build artifacts, and common junk
        p = Path(path)
        if p.name.startswith('.'):
            return False
        if p.suffix in ('.pyc', '.pyo', '.o', '.so', '.dll', '.exe',
                        '.log', '.tmp', '.cache', '.lock'):
            return False
        if any(part.startswith('.') for part in p.parts):
            return False
        return True
    
    def _debounced_process(self, path: str, event_type: str):
        now = time.time()
        if now - self._last_event_time < self._debounce_seconds:
            return
        self._last_event_time = now
        
        asyncio.create_task(self.plugin._handle_file_event(path, event_type))


class WorkspacePlugin(DeepPlugin):
    """
    Tracks your active projects, file changes, and git activity.
    """

    name = "workspace"
    version = "1.0.0"
    description = "Monitors project directories, git activity, and code context"
    author = "DEEP"

    def __init__(self, plugin_manager):
        super().__init__(plugin_manager)
        
        # Configuration
        self.watch_dirs: List[Path] = []
        self._load_watch_dirs()
        
        # State
        self.projects: Dict[str, Dict[str, Any]] = {}
        self.active_project: Optional[str] = None
        self.recent_files: List[Dict[str, Any]] = []
        self._observer: Optional[Any] = None
        self._event_handler: Optional[WorkspaceEventHandler] = None
        
        # Stats
        self.files_changed_today = 0
        self.last_scan_time: Optional[datetime] = None

    def _load_watch_dirs(self):
        """Load directories to watch."""
        default = Path.home() / "Projects"
        if default.exists():
            self.watch_dirs.append(default)
        
        # Also check common locations
        for candidate in [
            Path.home() / "projects",
            Path.home() / "workspace",
            Path.home() / "code",
            Path.home() / "dev",
        ]:
            if candidate.exists() and candidate not in self.watch_dirs:
                self.watch_dirs.append(candidate)
        
        if not self.watch_dirs:
            logger.warning("[Workspace] No project directories found. Create ~/Projects")

    # ─── Lifecycle ───────────────────────────────────────────────────────────

    async def on_init(self):
        """Discover existing projects."""
        # Always register API endpoints even if optional deps are missing
        self.register_endpoint("GET", "/api/workspace/stats", self.api_stats)
        self.register_endpoint("GET", "/api/workspace/projects", self.api_projects)
        self.register_endpoint("GET", "/api/workspace/active", self.api_active)
        
        if not _WATCHDOG_AVAILABLE and not _GIT_AVAILABLE:
            logger.warning("[Workspace] No optional deps available. File/git monitoring disabled.")
            self._scan_all_projects()
            return
        
        self._scan_all_projects()

    async def on_start(self):
        """Start file system monitoring."""
        if _WATCHDOG_AVAILABLE:
            self._start_watching()
        
        # Register periodic scan. Pass the method itself (not a called coroutine)
        # so the periodic runner creates a FRESH coroutine each interval — a
        # single coroutine object can only be awaited once.
        self.register_background_task(
            "workspace_scan", self._periodic_scan, interval=60
        )

    async def on_stop(self):
        """Stop monitoring."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

    # ─── File Watching ───────────────────────────────────────────────────────

    def _start_watching(self):
        """Start watchdog observer."""
        if not _WATCHDOG_AVAILABLE or not self.watch_dirs:
            return
        
        self._event_handler = WorkspaceEventHandler(self)
        self._observer = Observer()
        
        for watch_dir in self.watch_dirs:
            try:
                self._observer.schedule(self._event_handler, str(watch_dir), recursive=True)
                logger.info(f"[Workspace] Watching {watch_dir}")
            except Exception as e:
                logger.warning(f"[Workspace] Failed to watch {watch_dir}: {e}")
        
        self._observer.start()

    async def _handle_file_event(self, path: str, event_type: str):
        """Process a file system event."""
        p = Path(path)
        
        # Find which project this belongs to
        project_name = self._get_project_for_path(p)
        if not project_name:
            return
        
        # Update project stats
        self._update_project_activity(project_name, p)
        
        # Track recent file
        self.recent_files.insert(0, {
            "path": str(p),
            "project": project_name,
            "event": event_type,
            "time": datetime.utcnow().isoformat(),
        })
        if len(self.recent_files) > 20:
            self.recent_files = self.recent_files[:20]
        
        self.files_changed_today += 1
        
        # Emit event for UI
        self.pm.emit(self.name, "file_changed", {
            "project": project_name,
            "file": p.name,
            "event": event_type,
        })

    # ─── Git Integration ─────────────────────────────────────────────────────

    def _scan_all_projects(self):
        """Discover all projects in watched directories."""
        for watch_dir in self.watch_dirs:
            for item in watch_dir.iterdir():
                if item.is_dir():
                    self._scan_project(item)

    def _scan_project(self, path: Path):
        """Scan a single project directory."""
        name = path.name
        project = {
            "name": name,
            "path": str(path),
            "last_activity": None,
            "files_changed": 0,
            "git_branch": None,
            "git_last_commit": None,
            "git_dirty": False,
            "is_git_repo": False,
        }
        
        # Check git status
        if _GIT_AVAILABLE:
            try:
                repo = git.Repo(path)
                project["is_git_repo"] = True
                project["git_branch"] = repo.active_branch.name
                project["git_last_commit"] = repo.head.commit.committed_datetime.isoformat() if repo.head.commit else None
                project["git_dirty"] = repo.is_dirty()
            except (git.InvalidGitRepositoryError, git.NoSuchPathError):
                pass
            except Exception as e:
                logger.debug(f"[Workspace] Git check failed for {name}: {e}")
        
        self.projects[name] = project

    def _update_project_activity(self, name: str, file_path: Path):
        """Update activity timestamp for a project."""
        if name in self.projects:
            self.projects[name]["last_activity"] = datetime.utcnow().isoformat()
            self.projects[name]["files_changed"] += 1
            self.active_project = name

    def _get_project_for_path(self, path: Path) -> Optional[str]:
        """Find which project a file belongs to."""
        for watch_dir in self.watch_dirs:
            try:
                rel = path.relative_to(watch_dir)
                return rel.parts[0] if rel.parts else None
            except ValueError:
                continue
        return None

    async def _periodic_scan(self):
        """Periodic background scan. Refresh git status."""
        self._scan_all_projects()
        self.last_scan_time = datetime.utcnow()
        logger.debug("[Workspace] Periodic scan complete")

    # ─── API Handlers ────────────────────────────────────────────────────────

    async def api_stats(self):
        """GET /api/workspace/stats"""
        active = self.active_project
        active_info = self.projects.get(active, {}) if active else {}
        
        return {
            "active_project": active,
            "projects_tracked": len(self.projects),
            "files_changed_today": self.files_changed_today,
            "git_repos": sum(1 for p in self.projects.values() if p.get("is_git_repo")),
            "watch_dirs": [str(d) for d in self.watch_dirs],
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
        }

    async def api_projects(self):
        """GET /api/workspace/projects"""
        # Sort by most recent activity
        sorted_projects = sorted(
            self.projects.values(),
            key=lambda p: p.get("last_activity") or "",
            reverse=True
        )
        return {"projects": sorted_projects[:10]}

    async def api_active(self):
        """GET /api/workspace/active"""
        if not self.active_project or self.active_project not in self.projects:
            return {"active": None}
        return {"active": self.projects[self.active_project]}
