"""core/domain/interfaces.py — Abstract protocols for DEEP components."""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional, Protocol


class LLMClient(Protocol):
    """Protocol for LLM client implementations."""

    model_name: str = "unknown"
    is_available: bool = False

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
    """Protocol for tool execution."""

    def describe_tools(self) -> str: ...

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
