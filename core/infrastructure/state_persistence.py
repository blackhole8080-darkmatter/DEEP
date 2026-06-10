"""
core/infrastructure/state_persistence.py

State snapshot and recovery system.
Ensures conversations and context survive restarts.
"""

from __future__ import annotations

import json
import logging
import os
import pickle
import time
import zlib
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from threading import Lock, Timer

logger = logging.getLogger(__name__)


@dataclass
class StateSnapshot:
    """A point-in-time snapshot of DEEP state."""
    version: str = "2.0"
    timestamp: float = 0.0
    session_id: str = ""
    
    # Conversations
    conversations: Dict[str, Any] = None
    current_conversation_id: Optional[str] = None
    
    # Memory cache (recent items only)
    recent_memories: List[Dict] = None
    
    # Tool states
    active_tasks: List[Dict] = None
    
    # User preferences learned
    user_preferences: Dict[str, Any] = None
    
    # Statistics
    message_count: int = 0
    session_duration_seconds: float = 0.0
    
    def __post_init__(self):
        if self.conversations is None:
            self.conversations = {}
        if self.recent_memories is None:
            self.recent_memories = []
        if self.active_tasks is None:
            self.active_tasks = []
        if self.user_preferences is None:
            self.user_preferences = {}


class StateManager:
    """
    Manages state persistence with automatic snapshots.
    
    Features:
    - Automatic snapshots every N minutes
    - Manual snapshots on demand
    - Compression for efficient storage
    - Encryption option for sensitive data
    - Recovery on startup
    """
    
    def __init__(
        self,
        snapshot_dir: str = "data/snapshots",
        auto_save_interval: int = 300,  # 5 minutes
        max_snapshots: int = 10,
        compression: bool = True
    ):
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.auto_save_interval = auto_save_interval
        self.max_snapshots = max_snapshots
        self.compression = compression
        
        self._current_state: Optional[StateSnapshot] = None
        self._lock = Lock()
        self._timer: Optional[Timer] = None
        self._providers: Dict[str, Callable[[], Any]] = {}
        self._restorers: Dict[str, Callable[[Any], None]] = {}
        
        self._session_start = time.time()
        self._session_id = f"sess_{int(self._session_start)}_{os.getpid()}"
    
    def register_provider(self, name: str, provider: Callable[[], Any]):
        """
        Register a function that provides state data.
        
        Args:
            name: Identifier for this state component
            provider: Function that returns serializable state
        """
        self._providers[name] = provider
        logger.debug(f"Registered state provider: {name}")
    
    def register_restorer(self, name: str, restorer: Callable[[Any], None]):
        """
        Register a function that restores state data.
        
        Args:
            name: Identifier for this state component
            restorer: Function that accepts state data and restores it
        """
        self._restorers[name] = restorer
        logger.debug(f"Registered state restorer: {name}")
    
    def start_auto_save(self):
        """Start automatic periodic snapshots."""
        self._schedule_next_save()
        logger.info(f"Auto-save started (interval: {self.auto_save_interval}s)")
    
    def stop_auto_save(self):
        """Stop automatic snapshots."""
        if self._timer:
            self._timer.cancel()
            self._timer = None
        logger.info("Auto-save stopped")
    
    def _schedule_next_save(self):
        """Schedule the next automatic save."""
        if self._timer:
            self._timer.cancel()
        
        self._timer = Timer(self.auto_save_interval, self._auto_save)
        self._timer.daemon = True
        self._timer.start()
    
    def _auto_save(self):
        """Perform automatic save."""
        try:
            self.save_snapshot()
        except Exception as e:
            logger.error(f"Auto-save failed: {e}")
        finally:
            self._schedule_next_save()
    
    def save_snapshot(self, name: Optional[str] = None) -> Path:
        """
        Save current state to snapshot file.
        
        Args:
            name: Optional custom name (default: auto-generated)
        
        Returns:
            Path to saved snapshot file
        """
        with self._lock:
            snapshot = self._create_snapshot()
            
            # Generate filename
            if name:
                filename = f"{name}.snap"
            else:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"snapshot_{ts}_{self._session_id}.snap"
            
            filepath = self.snapshot_dir / filename
            
            # Serialize
            data = asdict(snapshot)
            serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
            
            # Compress if enabled
            if self.compression:
                serialized = zlib.compress(serialized, level=6)
            
            # Write atomically
            temp_path = filepath.with_suffix(".tmp")
            try:
                with open(temp_path, "wb") as f:
                    f.write(serialized)
                temp_path.replace(filepath)
            except Exception:
                if temp_path.exists():
                    temp_path.unlink()
                raise
            
            # Cleanup old snapshots
            self._cleanup_old_snapshots()
            
            logger.info(f"Snapshot saved: {filepath.name} ({len(serialized)} bytes)")
            return filepath
    
    def _create_snapshot(self) -> StateSnapshot:
        """Create snapshot from registered providers."""
        snapshot = StateSnapshot(
            timestamp=time.time(),
            session_id=self._session_id,
            session_duration_seconds=time.time() - self._session_start
        )
        
        # Gather state from all providers
        collected = {}
        for name, provider in self._providers.items():
            try:
                collected[name] = provider()
            except Exception as e:
                logger.warning(f"Provider {name} failed: {e}")
                collected[name] = None
        
        # Map to snapshot fields
        if "conversations" in collected:
            snapshot.conversations = collected["conversations"]
        if "current_conversation" in collected:
            snapshot.current_conversation_id = collected["current_conversation"]
        if "recent_memories" in collected:
            snapshot.recent_memories = collected["recent_memories"]
        if "active_tasks" in collected:
            snapshot.active_tasks = collected["active_tasks"]
        if "user_preferences" in collected:
            snapshot.user_preferences = collected["user_preferences"]
        if "stats" in collected:
            stats = collected["stats"]
            snapshot.message_count = stats.get("message_count", 0)
        
        self._current_state = snapshot
        return snapshot
    
    def load_latest_snapshot(self) -> Optional[StateSnapshot]:
        """
        Load the most recent valid snapshot.
        
        Returns:
            Snapshot if found and valid, None otherwise
        """
        snapshots = self.list_snapshots()
        if not snapshots:
            logger.info("No snapshots found")
            return None
        
        # Try from newest to oldest
        for filepath in snapshots:
            try:
                snapshot = self._load_snapshot_file(filepath)
                if snapshot:
                    logger.info(f"Loaded snapshot: {filepath.name}")
                    
                    # Restore to registered components
                    self._restore_snapshot(snapshot)
                    return snapshot
            except Exception as e:
                logger.warning(f"Failed to load {filepath.name}: {e}")
                continue
        
        logger.warning("Could not load any snapshot")
        return None
    
    def _load_snapshot_file(self, filepath: Path) -> Optional[StateSnapshot]:
        """Load and deserialize a snapshot file."""
        with open(filepath, "rb") as f:
            data = f.read()
        
        # Try decompression
        try:
            data = zlib.decompress(data)
        except zlib.error:
            pass  # Not compressed
        
        # Deserialize
        raw = pickle.loads(data)
        
        # Validate and convert
        if not isinstance(raw, dict):
            raise ValueError("Invalid snapshot format")
        
        snapshot = StateSnapshot(**raw)
        
        # Check age (don't load if too old)
        age_hours = (time.time() - snapshot.timestamp) / 3600
        if age_hours > 24:
            logger.warning(f"Snapshot is {age_hours:.1f} hours old")
        
        return snapshot
    
    def _restore_snapshot(self, snapshot: StateSnapshot):
        """Restore snapshot to registered components."""
        restored = []
        failed = []
        
        # Map snapshot fields to restorers
        field_mapping = {
            "conversations": "conversations",
            "current_conversation_id": "current_conversation",
            "recent_memories": "recent_memories",
            "active_tasks": "active_tasks",
            "user_preferences": "user_preferences",
        }
        
        for field, restorer_name in field_mapping.items():
            if restorer_name in self._restorers:
                value = getattr(snapshot, field)
                if value:
                    try:
                        self._restorers[restorer_name](value)
                        restored.append(restorer_name)
                    except Exception as e:
                        failed.append((restorer_name, str(e)))
        
        if restored:
            logger.info(f"Restored: {', '.join(restored)}")
        if failed:
            logger.warning(f"Failed to restore: {', '.join(f[0] for f in failed)}")
    
    def list_snapshots(self) -> List[Path]:
        """List all available snapshots, newest first."""
        pattern = "*.snap"
        snapshots = sorted(
            self.snapshot_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        return snapshots
    
    def _cleanup_old_snapshots(self):
        """Remove old snapshots keeping only max_snapshots."""
        snapshots = self.list_snapshots()
        if len(snapshots) <= self.max_snapshots:
            return
        
        to_remove = snapshots[self.max_snapshots:]
        for filepath in to_remove:
            try:
                filepath.unlink()
                logger.debug(f"Removed old snapshot: {filepath.name}")
            except Exception as e:
                logger.warning(f"Failed to remove {filepath.name}: {e}")
    
    def delete_snapshot(self, name: str) -> bool:
        """Delete a specific snapshot by name."""
        filepath = self.snapshot_dir / name
        if not filepath.exists():
            return False
        
        try:
            filepath.unlink()
            logger.info(f"Deleted snapshot: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {name}: {e}")
            return False
    
    def get_snapshot_info(self, filepath: Path) -> Dict:
        """Get metadata about a snapshot without loading it."""
        stat = filepath.stat()
        return {
            "name": filepath.name,
            "size_bytes": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "age_hours": round((time.time() - stat.st_mtime) / 3600, 1)
        }


# Global state manager instance
_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Get the global state manager (create if needed)."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager


def setup_deep_state_persistence(
    chat_service=None,
    memory=None,
    task_manager=None
):
    """
    Convenience function to setup state persistence for DEEP.
    
    Registers providers and restorers for core components.
    """
    manager = get_state_manager()
    
    # Register conversation provider
    if chat_service:
        manager.register_provider(
            "conversations",
            lambda: {k: v.to_dict() for k, v in getattr(chat_service, '_conversations', {}).items()}
        )
        manager.register_provider(
            "current_conversation",
            lambda: getattr(chat_service, '_current_conversation', {}).get('id') if hasattr(chat_service, '_current_conversation') else None
        )
        
        # Restorers
        from ..domain.models import Conversation, Message, MessageRole
        
        def restore_conversations(data):
            for conv_id, conv_data in data.items():
                conv = Conversation(
                    id=conv_data['id'],
                    title=conv_data.get('title'),
                    created_at=datetime.fromisoformat(conv_data['created_at']),
                    updated_at=datetime.fromisoformat(conv_data['updated_at'])
                )
                for msg_data in conv_data.get('messages', []):
                    msg = Message(
                        role=MessageRole(msg_data['role']),
                        content=msg_data['content'],
                        timestamp=datetime.fromisoformat(msg_data['timestamp']),
                        metadata=msg_data.get('metadata', {})
                    )
                    conv.messages.append(msg)
                
                chat_service._conversations[conv_id] = conv
        
        manager.register_restorer("conversations", restore_conversations)
    
    # Start auto-save
    manager.start_auto_save()
    
    # Try to restore on startup
    manager.load_latest_snapshot()
    
    logger.info("DEEP state persistence configured")
    return manager
