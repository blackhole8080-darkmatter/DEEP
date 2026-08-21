"""core/domain/interfaces.py — Abstract protocols for DEEP components."""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional, Protocol


class LLMClient(Protocol):
    """Protocol for LLM client implementations."""

    model_name: str = "unknown"
    is_available: bool = False
    #: True when this client can be handed images alongside the prompt. Declared
    #: rather than assumed: DEEP's default local model cannot see, and sending a
    #: picture to a text-only model either errors or is silently ignored — the
    #: second being worse, because the answer then reads as though the model
    #: looked. Callers check this and say so when the answer is text-only.
    supports_images: bool = False

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str: ...

    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[str]: ...

    def health_check(self) -> Any: ...


class ToolExecutor(Protocol):
    """Protocol for tool execution.

    ``list_tools`` and ``available_tools`` are part of the contract because the
    brain validates a model-chosen tool name against them before executing.
    They were used by AsyncBrain but never declared here, and the one real
    implementation did not provide them — so every tool call raised
    AttributeError and killed the turn. Declared, a missing one is a type error
    rather than a runtime surprise.
    """

    def describe_tools(self) -> str: ...

    def list_tools(self) -> List[str]: ...

    #: Name → {"description": str, "args": {arg: hint}}.
    available_tools: Dict[str, Dict[str, Any]]

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any: ...


class MemoryRepository(Protocol):
    """Protocol for long-term memory storage."""

    is_available: bool = False

    def store(self, key: str, value: Any) -> None: ...

    def recall(self, query: str, k: int = 5) -> List[Any]: ...


class Agent(Protocol):
    """Protocol for DEEP agent implementations."""

    async def process(
        self,
        user_input: str,
        context: str = "",
        tools: Optional[ToolExecutor] = None,
    ) -> Any: ...

    async def process_stream(
        self,
        user_input: str,
        context: str = "",
        tools: Optional[ToolExecutor] = None,
    ) -> AsyncIterator[str]: ...

    def health_check(self) -> Any: ...
