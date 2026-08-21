"""core/domain/models.py — Dataclasses for DEEP domain objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


@dataclass
class ToolImage:
    """An image a tool produced, for a model that can actually look at it.

    Carried as base64 rather than raw bytes because that is the shape every
    provider wants on the wire, and re-encoding per loop of the tool cycle is
    waste. ``label`` is the text fallback: when the active model cannot see —
    DEEP's default llama3.2 cannot — the label is what the model gets instead,
    so the turn degrades to "there is a screenshot I cannot show you" rather
    than to silence.
    """

    data: str
    mime_type: str = "image/png"
    label: str = "an image"

    @property
    def approx_bytes(self) -> int:
        """Decoded size, near enough for a budget check without decoding."""
        return len(self.data) * 3 // 4


@dataclass
class ToolResult:
    ok: bool = True
    content: str = ""
    tool_name: str = ""
    error: str = ""
    #: Images the tool produced. Empty for almost every tool, so nothing that
    #: does not deal in pictures has to know this field exists.
    images: List["ToolImage"] = field(default_factory=list)


@dataclass
class AgentLoopResult:
    final_response: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    thinking: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    role: MessageRole = MessageRole.USER
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    id: str = ""
    title: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: List[Message] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [
                {
                    "role": m.role.value,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "metadata": m.metadata,
                }
                for m in self.messages
            ],
        }


@dataclass
class MemoryEntry:
    key: str = ""
    value: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
