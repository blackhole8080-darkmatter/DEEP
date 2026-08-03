"""
core/infrastructure/llm_clients.py

Concrete LLM client implementations with:
- Circuit breaker protection
- Async streaming support
- Health check capability
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator, Optional

import aiohttp
import requests

from ..domain.interfaces import LLMClient
from ..resilience import CircuitBreaker, CircuitBreakerConfig, get_breaker
from ..health import ComponentHealth, ComponentStatus

logger = logging.getLogger(__name__)


class OllamaClient(LLMClient):
    """
    Async Ollama client with circuit breaker and streaming support.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        timeout: float = 60.0
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._breaker = get_breaker("ollama") or CircuitBreaker(
            "ollama",
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30.0,
                timeout_seconds=timeout
            )
        )
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self, streaming: bool = False) -> aiohttp.ClientSession:
        """Get or create aiohttp session with optimized settings."""
        if self._session is None or self._session.closed:
            # Connection pooling settings
            connector = aiohttp.TCPConnector(
                limit=10,  # Max concurrent connections
                limit_per_host=5,  # Max per host
                enable_cleanup_closed=True,
                force_close=False,
            )
            
            if streaming:
                timeout = aiohttp.ClientTimeout(
                    total=None,
                    sock_connect=30,
                    sock_read=60
                )
            else:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    "Connection": "keep-alive",
                    "Keep-Alive": "timeout=60, max=100"
                }
            )
        return self._session
    
    async def close(self):
        """Close session properly."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    @property
    def model_name(self) -> str:
        return self.model
    
    @property
    def is_available(self) -> bool:
        """Quick sync check for availability."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except:
            return False
    
    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Synchronous generation (for compatibility)."""
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                self._generate_sync,
                system_prompt,
                user_prompt,
                **kwargs
            )
            return future.result(timeout=self.timeout)
    
    def _generate_sync(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Internal sync implementation with circuit breaker."""
        def _call():
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "system": system_prompt,
                    "prompt": user_prompt,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", 0.7),
                        "num_predict": kwargs.get("max_tokens", 512)
                    }
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json().get("response", "")
        
        try:
            return self._breaker.call(_call)
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise
    
    async def generate_stream(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Async streaming generation with optimized token delivery.
        Batches small tokens for smoother frontend display.
        """
        session = await self._get_session(streaming=True)
        
        try:
            async with session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "system": system_prompt,
                    "prompt": user_prompt,
                    "stream": True,
                    "options": {
                        "temperature": kwargs.get("temperature", 0.7),
                        "num_predict": kwargs.get("max_tokens", 512)
                    }
                }
            ) as response:
                response.raise_for_status()
                
                # Buffer small tokens for smoother display
                token_buffer = []
                buffer_size = 0
                last_yield_time = asyncio.get_event_loop().time()
                
                # NDJSON stream: accumulate bytes and split on newlines
                raw_buffer = b""
                async for chunk in response.content.iter_any():
                    if not chunk:
                        continue
                    raw_buffer += chunk
                    # Split on newlines; keep the last partial line in raw_buffer
                    while b"\n" in raw_buffer:
                        line, raw_buffer = raw_buffer.split(b"\n", 1)
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                token = data["response"]
                                token_buffer.append(token)
                                buffer_size += len(token)
                                
                                # Yield conditions:
                                # 1. Buffer has 10+ tokens
                                # 2. Buffer has 50+ characters
                                # 3. 50ms passed since last yield
                                current_time = asyncio.get_event_loop().time()
                                time_since_yield = (current_time - last_yield_time) * 1000
                                
                                if (len(token_buffer) >= 10 or 
                                    buffer_size >= 50 or 
                                    time_since_yield >= 50):
                                    yield "".join(token_buffer)
                                    token_buffer = []
                                    buffer_size = 0
                                    last_yield_time = current_time
                                    
                            if data.get("done"):
                                # Yield any remaining tokens
                                if token_buffer:
                                    yield "".join(token_buffer)
                                raw_buffer = b""
                                break
                                
                        except json.JSONDecodeError:
                            continue
                
                # Final flush
                if token_buffer:
                    yield "".join(token_buffer)
                # Handle any trailing line without newline
                if raw_buffer.strip():
                    try:
                        data = json.loads(raw_buffer)
                        if "response" in data:
                            yield data["response"]
                    except json.JSONDecodeError:
                        pass
                        
        except Exception as e:
            logger.error(f"Ollama streaming failed: {type(e).__name__}: {e}")
            raise
    
    def health_check(self) -> ComponentHealth:
        """Return health status."""
        import time
        
        start = time.time()
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            latency = (time.time() - start) * 1000
            
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                return ComponentHealth(
                    name="ollama",
                    status=ComponentStatus.OK,
                    latency_ms=latency,
                    message=f"Connected, {len(models)} models",
                    metadata={"models": models[:5], "target_model": self.model}
                )
            else:
                return ComponentHealth(
                    name="ollama",
                    status=ComponentStatus.DEGRADED,
                    latency_ms=latency,
                    message=f"Status {resp.status_code}"
                )
        except requests.exceptions.Timeout:
            return ComponentHealth(
                name="ollama",
                status=ComponentStatus.DEGRADED,
                latency_ms=5000,
                message="Connection timeout"
            )
        except Exception as e:
            return ComponentHealth(
                name="ollama",
                status=ComponentStatus.FAILED,
                latency_ms=0,
                message=f"Error: {str(e)[:100]}"
            )


class ClaudeClient(LLMClient):
    """
    Async Anthropic Claude client with circuit breaker.
    """
    
    API_URL = "https://api.anthropic.com/v1/messages"
    
    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-latest",
        timeout: float = 30.0
    ):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._breaker = get_breaker("claude") or CircuitBreaker(
            "claude",
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60.0,
                timeout_seconds=timeout
            )
        )
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self, streaming: bool = False) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            if streaming:
                timeout = aiohttp.ClientTimeout(
                    total=None,
                    sock_connect=30,
                    sock_read=60
                )
            else:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                timeout=timeout
            )
        return self._session
    
    @property
    def model_name(self) -> str:
        return self.model
    
    @property
    def is_available(self) -> bool:
        """Check API key is valid."""
        if not self.api_key or self.api_key == "your-api-key-here":
            return False
        return True
    
    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Synchronous generation."""
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                self._generate_sync,
                system_prompt,
                user_prompt,
                **kwargs
            )
            return future.result(timeout=self.timeout)
    
    def _generate_sync(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Internal sync implementation."""
        def _call():
            response = requests.post(
                self.API_URL,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": self.model,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                    "max_tokens": kwargs.get("max_tokens", 1024),
                    "temperature": kwargs.get("temperature", 0.7)
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract text from content blocks
            content_blocks = data.get("content", [])
            text_parts = [
                block.get("text", "")
                for block in content_blocks
                if block.get("type") == "text"
            ]
            return "".join(text_parts)
        
        try:
            return self._breaker.call(_call)
        except Exception as e:
            logger.error(f"Claude generation failed: {e}")
            raise
    
    async def generate_stream(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        **kwargs
    ) -> AsyncIterator[str]:
        """Async streaming generation with token batching for smooth display."""
        session = await self._get_session(streaming=True)
        
        try:
            async with session.post(
                self.API_URL,
                json={
                    "model": self.model,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                    "max_tokens": kwargs.get("max_tokens", 1024),
                    "temperature": kwargs.get("temperature", 0.7),
                    "stream": True
                }
            ) as response:
                response.raise_for_status()
                
                # Token batching for smooth display
                token_buffer = []
                buffer_size = 0
                last_yield_time = asyncio.get_event_loop().time()
                
                async for line in response.content:
                    if not line or line.startswith(b":"):
                        continue
                    
                    # SSE format: data: {...}
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        json_str = line_str[6:]
                        if json_str == "[DONE]":
                            if token_buffer:
                                yield "".join(token_buffer)
                            break
                        
                        try:
                            data = json.loads(json_str)
                            delta = data.get("delta", {})
                            if "text" in delta:
                                token = delta["text"]
                                token_buffer.append(token)
                                buffer_size += len(token)
                                
                                # Yield conditions
                                current_time = asyncio.get_event_loop().time()
                                time_since_yield = (current_time - last_yield_time) * 1000
                                
                                if (len(token_buffer) >= 10 or 
                                    buffer_size >= 50 or 
                                    time_since_yield >= 50):
                                    yield "".join(token_buffer)
                                    token_buffer = []
                                    buffer_size = 0
                                    last_yield_time = current_time
                                    
                        except json.JSONDecodeError:
                            continue
                
                # Final flush
                if token_buffer:
                    yield "".join(token_buffer)
                            
        except Exception as e:
            logger.error(f"Claude streaming failed: {e}")
            raise
    
    def health_check(self) -> ComponentHealth:
        """Return health status."""
        if not self.is_available:
            return ComponentHealth(
                name="claude",
                status=ComponentStatus.FAILED,
                message="API key not configured"
            )
        
        import time
        start = time.time()
        
        try:
            # Lightweight models list call
            response = requests.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01"
                },
                timeout=5
            )
            latency = (time.time() - start) * 1000
            
            if response.status_code == 200:
                return ComponentHealth(
                    name="claude",
                    status=ComponentStatus.OK,
                    latency_ms=latency,
                    message="API key valid",
                    metadata={"model": self.model}
                )
            elif response.status_code == 401:
                return ComponentHealth(
                    name="claude",
                    status=ComponentStatus.FAILED,
                    latency_ms=latency,
                    message="Invalid API key"
                )
            else:
                return ComponentHealth(
                    name="claude",
                    status=ComponentStatus.DEGRADED,
                    latency_ms=latency,
                    message=f"Status {response.status_code}"
                )
        except Exception as e:
            return ComponentHealth(
                name="claude",
                status=ComponentStatus.DEGRADED,
                message=f"Connection error: {str(e)[:100]}"
            )
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()


class LLMClientPool:
    """
    Pool of LLM clients with failover support.
    Tries primary, falls back to secondary if primary fails.
    """
    
    def __init__(self, clients: list[LLMClient], prefer_order: list[int] = None):
        self.clients = clients
        self.prefer_order = prefer_order or list(range(len(clients)))
    
    async def generate_with_fallback(
        self, 
        system_prompt: str, 
        user_prompt: str,
        **kwargs
    ) -> str:
        """
        Generate with automatic failover.
        Tries clients in preference order until one succeeds.
        """
        last_error = None
        
        for idx in self.prefer_order:
            client = self.clients[idx]
            
            if not client.is_available:
                continue
            
            try:
                return await asyncio.wait_for(
                    client.generate_stream(system_prompt, user_prompt, **kwargs)
                    if hasattr(client, 'generate_stream')
                    else asyncio.to_thread(client.generate, system_prompt, user_prompt, **kwargs),
                    timeout=30.0
                )
            except Exception as e:
                last_error = e
                logger.warning(f"Client {client.model_name} failed: {e}, trying next...")
                continue
        
        # All clients failed
        raise RuntimeError(f"All LLM clients failed. Last error: {last_error}")
    
    def health_check_all(self) -> list[ComponentHealth]:
        """Check health of all clients."""
        return [c.health_check() for c in self.clients if hasattr(c, 'health_check')]
