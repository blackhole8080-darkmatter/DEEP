"""
multi_llm_router.py

Intelligent multi-LLM routing system for DEEP.

Features:
- Automatic provider selection based on task type
- Fallback chain for reliability
- Cost/performance optimization
- Parallel query execution for comparison

Supported providers:
- Ollama (local, default)
- OpenAI (GPT-4, GPT-3.5)
- Claude (Anthropic)
- Gemini (Google)
- Mistral

Usage:
    from DEEP.core.multi_llm_router import MultiLLMRouter
    
    router = MultiLLMRouter(settings)
    
    # Smart routing - picks best model for task
    response = await router.generate("Write Python code...", task_type="code")
    
    # Multi-agent mode - multiple AIs discuss
    consensus = await router.multi_agent_discuss("Should I invest in Tesla?")
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Optional, Dict, List, Any, AsyncIterator, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import time

from .config import Settings

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers"""
    OLLAMA = "ollama"          # Local, free, private
    OPENAI = "openai"         # GPT-4, GPT-3.5
    CLAUDE = "claude"         # Anthropic
    GEMINI = "gemini"         # Google
    MISTRAL = "mistral"       # Mistral AI


class TaskType(Enum):
    """Task categories for intelligent routing"""
    GENERAL = "general"       # Simple Q&A
    CODE = "code"             # Programming
    CREATIVE = "creative"     # Writing, stories
    ANALYSIS = "analysis"     # Complex reasoning
    RESEARCH = "research"     # Deep investigation
    CHAT = "chat"             # Casual conversation
    SUMMARY = "summary"       # Summarization
    PHYSICS = "physics"        # Math-heavy, symbolic reasoning
    EXPLOIT = "exploit"        # CVE/security analysis
    RF_ANALYSIS = "rf_analysis" # Spectrum/signal pattern recognition
    PROTOCOL_RE = "protocol_re" # Binary parsing, dissector generation
    ROBOTICS = "robotics"       # Control theory, kinematics
    OSINT = "osint"            # Passive reconnaissance synthesis


@dataclass
class LLMResponse:
    """Standardized response from any LLM"""
    text: str
    provider: LLMProvider
    model: str
    latency_ms: float
    cost_estimate: float  # USD
    tokens_used: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderConfig:
    """Configuration for a specific LLM provider"""
    provider: LLMProvider
    api_key: Optional[str]
    model: str
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1024
    priority: int = 5  # Lower = higher priority
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    enabled: bool = True


class LLMClient:
    """Base class for LLM clients"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResponse:
        raise NotImplementedError
    
    async def generate_stream(self, system_prompt: str, user_prompt: str, **kwargs) -> AsyncIterator[str]:
        raise NotImplementedError
    
    async def health_check(self) -> bool:
        raise NotImplementedError
    
    async def close(self):
        if self.session:
            await self.session.close()


class OllamaClient(LLMClient):
    """Ollama local LLM client"""
    
    async def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResponse:
        start = time.time()
        session = await self._get_session()
        
        url = f"{self.config.base_url or 'http://localhost:11434'}/api/chat"
        payload = {
            "model": self.config.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "options": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "num_predict": kwargs.get("max_tokens", self.config.max_tokens)
            }
        }
        
        # Non-streaming: must wait for the full response, which is slow on CPU.
        # Cap total generously and cap connect separately.
        gen_timeout = aiohttp.ClientTimeout(total=300, connect=10)
        async with session.post(url, json=payload, timeout=gen_timeout) as resp:
            data = await resp.json()
            text = data.get("message", {}).get("content", "")
        
        latency = (time.time() - start) * 1000
        return LLMResponse(
            text=text,
            provider=LLMProvider.OLLAMA,
            model=self.config.model,
            latency_ms=latency,
            cost_estimate=0.0  # Free
        )
    
    async def generate_stream(self, system_prompt: str, user_prompt: str, **kwargs) -> AsyncIterator[str]:
        session = await self._get_session()
        url = f"{self.config.base_url or 'http://localhost:11434'}/api/chat"
        
        payload = {
            "model": self.config.model,
            "stream": True,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        
        # Streaming: cap inactivity (sock_read), NOT total duration — otherwise a
        # slow-but-healthy CPU generation gets hard-killed mid-stream. Abort only
        # if Ollama stalls with no new data for sock_read seconds.
        stream_timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_read=180)
        async with session.post(url, json=payload, timeout=stream_timeout) as resp:
            async for line in resp.content:
                if line:
                    try:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
                    except:
                        pass
    
    async def health_check(self) -> bool:
        try:
            session = await self._get_session()
            url = f"{self.config.base_url or 'http://localhost:11434'}/api/tags"
            async with session.get(url, timeout=5) as resp:
                return resp.status == 200
        except:
            return False


class OpenAIClient(LLMClient):
    """OpenAI GPT client - supports new project-based API keys"""
    
    async def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResponse:
        start = time.time()
        session = await self._get_session()
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Use gpt-4o-mini for better availability/cost, fallback to gpt-3.5-turbo
        model = self.config.model
        if model == "gpt-4":
            model = "gpt-4o-mini"  # Better availability
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens)
        }
        
        async with session.post(url, headers=headers, json=payload, timeout=60) as resp:
            if resp.status != 200:
                text_content = await resp.text()
                raise Exception(f"OpenAI API error {resp.status}: {text_content[:200]}")
            
            data = await resp.json()
            text = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
        
        latency = (time.time() - start) * 1000
        cost = (tokens / 1000) * (self.config.cost_per_1k_input + self.config.cost_per_1k_output) / 2
        
        return LLMResponse(
            text=text,
            provider=LLMProvider.OPENAI,
            model=self.config.model,
            latency_ms=latency,
            cost_estimate=cost,
            tokens_used=tokens
        )
    
    async def generate_stream(self, system_prompt: str, user_prompt: str, **kwargs) -> AsyncIterator[str]:
        session = await self._get_session()
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": True
        }
        
        async with session.post(url, headers=headers, json=payload, timeout=60) as resp:
            async for line in resp.content:
                if line.startswith(b"data: "):
                    try:
                        data = json.loads(line[6:])
                        if "choices" in data and data["choices"]:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except:
                        pass
    
    async def health_check(self) -> bool:
        return self.config.api_key is not None and len(self.config.api_key) > 10


class ClaudeClient(LLMClient):
    """Anthropic Claude client"""
    
    async def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResponse:
        start = time.time()
        session = await self._get_session()
        
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.config.model,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}]
        }
        
        async with session.post(url, headers=headers, json=payload, timeout=60) as resp:
            data = await resp.json()
            text = "".join([b.get("text", "") for b in data.get("content", [])])
            tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
        
        latency = (time.time() - start) * 1000
        cost = (tokens / 1000) * (self.config.cost_per_1k_input + self.config.cost_per_1k_output) / 2
        
        return LLMResponse(
            text=text,
            provider=LLMProvider.CLAUDE,
            model=self.config.model,
            latency_ms=latency,
            cost_estimate=cost,
            tokens_used=tokens
        )
    
    async def health_check(self) -> bool:
        return self.config.api_key is not None and len(self.config.api_key) > 10


class GeminiClient(LLMClient):
    """Google Gemini client - supports v1beta API"""
    
    async def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResponse:
        start = time.time()
        session = await self._get_session()
        
        # Try different model name formats and API versions
        model_formats = [
            f"models/{self.config.model}",  # Full path format
            self.config.model.replace("models/", ""),  # Short format
            "gemini-pro",  # Fallback to stable model
        ]
        
        for api_version in ["v1beta", "v1"]:
            for model_name in model_formats:
                try:
                    url = f"https://generativelanguage.googleapis.com/{api_version}/{model_name}:generateContent"
                    params = {"key": self.config.api_key}
                    
                    payload = {
                        "contents": [{
                            "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]
                        }],
                        "generationConfig": {
                            "temperature": kwargs.get("temperature", self.config.temperature),
                            "maxOutputTokens": kwargs.get("max_tokens", self.config.max_tokens)
                        }
                    }
                    
                    async with session.post(url, params=params, json=payload, timeout=60) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            if "404" in error_text:
                                continue  # Try next model format
                            raise Exception(f"Gemini API {resp.status}: {error_text[:200]}")
                        
                        data = await resp.json()
                        
                        # Handle different response formats
                        if "candidates" in data and data["candidates"]:
                            candidate = data["candidates"][0]
                            if "content" in candidate and "parts" in candidate["content"]:
                                text = candidate["content"]["parts"][0].get("text", "")
                            else:
                                text = str(candidate)
                        else:
                            text = str(data)
                        
                        latency = (time.time() - start) * 1000
                        return LLMResponse(
                            text=text,
                            provider=LLMProvider.GEMINI,
                            model=model_name,
                            latency_ms=latency,
                            cost_estimate=0.0
                        )
                        
                except Exception as e:
                    if "404" in str(e):
                        continue  # Try next format
                    if api_version == "v1" and model_name == model_formats[-1]:
                        raise  # Last attempt failed
                    continue
        
        raise Exception(f"Gemini API failed for all model formats: {model_formats}")
    
    async def health_check(self) -> bool:
        return self.config.api_key is not None and len(self.config.api_key) > 10


class MultiLLMRouter:
    """
    Intelligent router for multiple LLM providers.
    
    Automatically selects the best model for each task type,
    manages fallbacks, and optimizes for cost/performance.
    """
    
    # Task type → preferred provider mapping
    ROUTING_STRATEGY = {
        TaskType.CODE: [LLMProvider.CLAUDE, LLMProvider.OPENAI, LLMProvider.OLLAMA],
        TaskType.ANALYSIS: [LLMProvider.CLAUDE, LLMProvider.OPENAI, LLMProvider.GEMINI, LLMProvider.OLLAMA],
        TaskType.RESEARCH: [LLMProvider.CLAUDE, LLMProvider.OPENAI, LLMProvider.GEMINI],
        TaskType.CREATIVE: [LLMProvider.OPENAI, LLMProvider.CLAUDE, LLMProvider.GEMINI],
        TaskType.GENERAL: [LLMProvider.OLLAMA, LLMProvider.GEMINI, LLMProvider.OPENAI],
        TaskType.CHAT: [LLMProvider.OLLAMA, LLMProvider.GEMINI, LLMProvider.OPENAI],
        TaskType.SUMMARY: [LLMProvider.OLLAMA, LLMProvider.GEMINI, LLMProvider.OPENAI],
        TaskType.PHYSICS: [LLMProvider.CLAUDE, LLMProvider.OPENAI, LLMProvider.OLLAMA],
        TaskType.EXPLOIT: [LLMProvider.CLAUDE, LLMProvider.OPENAI, LLMProvider.OLLAMA],
        TaskType.RF_ANALYSIS: [LLMProvider.OLLAMA, LLMProvider.GEMINI, LLMProvider.CLAUDE],
        TaskType.PROTOCOL_RE: [LLMProvider.CLAUDE, LLMProvider.OPENAI, LLMProvider.OLLAMA],
        TaskType.ROBOTICS: [LLMProvider.CLAUDE, LLMProvider.OPENAI, LLMProvider.OLLAMA],
        TaskType.OSINT: [LLMProvider.OLLAMA, LLMProvider.GEMINI, LLMProvider.CLAUDE],
    }
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.clients: Dict[LLMProvider, LLMClient] = {}
        self.performance_history: List[Dict] = []
        
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize all configured LLM clients"""
        
        # Ollama (local, always try first for privacy)
        self.clients[LLMProvider.OLLAMA] = OllamaClient(ProviderConfig(
            provider=LLMProvider.OLLAMA,
            api_key=None,
            model=getattr(self.settings, 'ollama_model', 'llama3.2'),
            base_url=getattr(self.settings, 'ollama_base_url', 'http://localhost:11434'),
            priority=1,
            enabled=True
        ))
        
        # OpenAI
        if getattr(self.settings, 'openai_api_key', None):
            self.clients[LLMProvider.OPENAI] = OpenAIClient(ProviderConfig(
                provider=LLMProvider.OPENAI,
                api_key=self.settings.openai_api_key,
                model=getattr(self.settings, 'openai_model', 'gpt-4'),
                priority=2,
                cost_per_1k_input=0.03,
                cost_per_1k_output=0.06,
                enabled=True
            ))
        
        # Claude
        if getattr(self.settings, 'claude_api_key', None):
            self.clients[LLMProvider.CLAUDE] = ClaudeClient(ProviderConfig(
                provider=LLMProvider.CLAUDE,
                api_key=self.settings.claude_api_key,
                model=getattr(self.settings, 'claude_model', 'claude-3-5-sonnet-latest'),
                priority=3,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
                enabled=True
            ))
        
        # Gemini
        if getattr(self.settings, 'gemini_api_key', None):
            self.clients[LLMProvider.GEMINI] = GeminiClient(ProviderConfig(
                provider=LLMProvider.GEMINI,
                api_key=self.settings.gemini_api_key,
                model=getattr(self.settings, 'gemini_model', 'gemini-pro'),
                priority=4,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                enabled=True
            ))
        
        logger.info(f"Initialized {len(self.clients)} LLM providers: {list(self.clients.keys())}")
    
    def classify_task(self, prompt: str) -> TaskType:
        """Classify the task type from the prompt"""
        prompt_lower = prompt.lower()
        
        # Expert domain classification
        if any(kw in prompt_lower for kw in ["quantum", "electromagnetic", "hamiltonian", "dispersion", "wavefunction", "lagrangian", "derive", "proof", "theorem", "physics", "plasma", "schrodinger", "schrödinger"]):
            return TaskType.PHYSICS
        if any(kw in prompt_lower for kw in ["cve", "exploit", "vulnerability", "hack", "penetration", "payload", "shellcode", "injection", "mitre", "attack", "red team", "cybersec"]):
            return TaskType.EXPLOIT
        if any(kw in prompt_lower for kw in ["frequency", "spectrum", "signal", "modulation", "sdr", "antenna", "wavelength", "iq", "fft", "waterfall"]):
            return TaskType.RF_ANALYSIS
        if any(kw in prompt_lower for kw in ["pcap", "packet", "protocol", "dissect", "binary", "reverse", "wireshark", "can bus", "modbus", "gatt", "ble"]):
            return TaskType.PROTOCOL_RE
        if any(kw in prompt_lower for kw in ["kinematics", "ros", "slam", "lidar", "pid", "trajectory", "inverse kinematics", "jacobian", "path planning", "robotics"]):
            return TaskType.ROBOTICS
        if any(kw in prompt_lower for kw in ["whois", "shodan", "crt.sh", "dnsrecon", "recon", "osint", "passive scan"]):
            return TaskType.OSINT

        # Code detection
        if any(kw in prompt_lower for kw in ['code', 'program', 'function', 'script', 'python', 'javascript', 'bug', 'error', 'debug']):
            return TaskType.CODE
        
        # Analysis
        if any(kw in prompt_lower for kw in ['analyze', 'compare', 'evaluate', 'assess', 'reasoning', 'logic']):
            return TaskType.ANALYSIS
        
        # Research
        if any(kw in prompt_lower for kw in ['research', 'investigate', 'find out', 'learn about', 'study']):
            return TaskType.RESEARCH
        
        # Creative
        if any(kw in prompt_lower for kw in ['write', 'story', 'creative', 'poem', 'essay', 'draft']):
            return TaskType.CREATIVE
        
        # Summary
        if any(kw in prompt_lower for kw in ['summarize', 'tl;dr', 'brief', 'overview', 'condense']):
            return TaskType.SUMMARY

        return TaskType.GENERAL

    # Provider tiers for complexity-based routing.
    STRONG_PROVIDERS = (LLMProvider.CLAUDE, LLMProvider.OPENAI)   # capable, paid
    CHEAP_PROVIDERS = (LLMProvider.OLLAMA, LLMProvider.GEMINI)    # local/free, fast

    _HARD_CUES = [
        'step by step', 'step-by-step', 'prove', 'derive', 'architecture',
        'design a', 'optimize', 'trade-off', 'tradeoff', 'algorithm', 'refactor',
        'debug', 'explain in detail', 'comprehensive', 'in depth', 'in-depth',
        'plan', 'strategy', 'analyze', 'compare', 'reasoning', 'why does', 'why is',
        'implement', 'multi-step', 'edge case', 'complexity',
    ]
    _EASY_CUES = [
        'hi', 'hello', 'hey', 'thanks', 'thank you', 'what time', 'weather',
        'remind me', 'add a task', 'list tasks', 'ok', 'yes', 'no',
    ]

    def estimate_complexity(self, prompt: str) -> str:
        """Heuristic easy/hard estimate to route cheap-for-easy, strong-for-hard."""
        p = (prompt or "").lower().strip()
        words = len(p.split())

        # Very short greetings/acks → easy
        if words <= 6 and any(p.startswith(c) or p == c for c in self._EASY_CUES):
            return "easy"

        score = 0
        if words > 120:
            score += 2
        elif words > 45:
            score += 1
        score += sum(1 for kw in self._HARD_CUES if kw in p)
        if '```' in prompt or 'def ' in prompt or 'class ' in prompt or 'function ' in p:
            score += 1
        if prompt.count('?') > 1:           # several questions at once
            score += 1
        return "hard" if score >= 2 else "easy"

    def _provider_order(self, task_type: TaskType, complexity: str) -> List[LLMProvider]:
        """Task-type order, reordered by complexity (stable within tier)."""
        base = self.ROUTING_STRATEGY.get(task_type, [LLMProvider.OLLAMA])
        if os.getenv("DEEP_COMPLEXITY_ROUTING", "1") in ("0", "false", "False"):
            return base
        if complexity == "hard":
            return sorted(base, key=lambda pr: 0 if pr in self.STRONG_PROVIDERS else 1)
        if complexity == "easy":
            return sorted(base, key=lambda pr: 0 if pr in self.CHEAP_PROVIDERS else 1)
        return base

    async def generate(
        self,
        user_prompt: str,
        system_prompt: str = "You are DEEP, a helpful AI assistant.",
        task_type: Optional[TaskType] = None,
        preferred_provider: Optional[LLMProvider] = None,
        fallback: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        Generate response with intelligent routing.
        
        Args:
            user_prompt: The user's request
            system_prompt: System instructions
            task_type: Force specific task type (auto-detected if None)
            preferred_provider: Force specific provider
            fallback: Try other providers if primary fails
        
        Returns:
            LLMResponse with text and metadata
        """
        if task_type is None:
            task_type = self.classify_task(user_prompt)

        complexity = self.estimate_complexity(user_prompt)

        # Get provider order for this task, reordered by complexity
        if preferred_provider:
            provider_order = [preferred_provider]
        else:
            provider_order = self._provider_order(task_type, complexity)

        # Try each provider in order
        last_error = None
        for provider in provider_order:
            client = self.clients.get(provider)
            if not client or not await client.health_check():
                continue

            try:
                logger.info(f"Routing to {provider.value} for {task_type.value} task ({complexity})")
                response = await client.generate(system_prompt, user_prompt, **kwargs)
                
                # Log performance
                self.performance_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "provider": provider.value,
                    "task_type": task_type.value,
                    "latency_ms": response.latency_ms,
                    "cost": response.cost_estimate
                })
                
                return response
                
            except Exception as e:
                logger.warning(f"{provider.value} failed: {e}")
                last_error = e
                if not fallback:
                    break
                continue
        
        # All providers failed
        raise Exception(f"All LLM providers failed. Last error: {last_error}")
    
    async def generate_stream(
        self,
        user_prompt: str,
        system_prompt: str = "You are DEEP, a helpful AI assistant.",
        task_type: Optional[TaskType] = None,
        preferred_provider: Optional[LLMProvider] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Streaming version of generate"""
        if task_type is None:
            task_type = self.classify_task(user_prompt)
        
        if preferred_provider:
            client = self.clients.get(preferred_provider)
        else:
            # Get first available provider for this task, reordered by complexity
            complexity = self.estimate_complexity(user_prompt)
            client = None
            for provider in self._provider_order(task_type, complexity):
                client = self.clients.get(provider)
                if client and await client.health_check():
                    break
        
        if not client:
            raise Exception("No LLM provider available")
        
        async for token in client.generate_stream(system_prompt, user_prompt, **kwargs):
            yield token
    
    async def multi_agent_discuss(
        self,
        topic: str,
        agents: Optional[List[LLMProvider]] = None,
        rounds: int = 2
    ) -> Dict[str, Any]:
        """
        Multiple AIs discuss a topic and reach consensus.
        
        Args:
            topic: The discussion topic/question
            agents: Which providers to include (default: all available)
            rounds: Number of discussion rounds
        
        Returns:
            Dict with individual responses and consensus
        """
        if agents is None:
            agents = [p for p, c in self.clients.items() if await c.health_check()]
        
        responses = {}
        
        # First round - initial opinions
        for provider in agents:
            client = self.clients.get(provider)
            if not client:
                continue
            
            system_prompt = f"You are an AI assistant participating in a multi-AI discussion. Share your perspective on: {topic}"
            try:
                response = await client.generate(system_prompt, topic)
                responses[provider.value] = {
                    "opinion": response.text,
                    "latency_ms": response.latency_ms,
                    "model": response.model
                }
            except Exception as e:
                responses[provider.value] = {"error": str(e)}
        
        # Additional rounds - AIs respond to each other (simplified)
        # In a full implementation, each AI would see others' responses
        
        # Generate consensus summary
        all_opinions = "\n\n".join([
            f"{name}: {data['opinion']}" 
            for name, data in responses.items() 
            if 'opinion' in data
        ])
        
        # Use most capable model for consensus
        consensus_provider = LLMProvider.CLAUDE if LLMProvider.CLAUDE in agents else agents[0]
        consensus_client = self.clients.get(consensus_provider)
        
        consensus_prompt = f"""Synthesize the following AI opinions into a balanced consensus:

{all_opinions}

Provide:
1. Areas of agreement
2. Unique insights from each perspective
3. Recommended course of action"""
        
        try:
            consensus = await consensus_client.generate(
                "You are a consensus builder. Synthesize multiple perspectives.",
                consensus_prompt
            )
            responses["consensus"] = consensus.text
        except:
            responses["consensus"] = "Could not generate consensus"
        
        return {
            "topic": topic,
            "rounds": rounds,
            "participants": [p.value for p in agents],
            "responses": responses,
            "final_consensus": responses.get("consensus", "")
        }
    
    async def compare_models(
        self,
        prompt: str,
        providers: Optional[List[LLMProvider]] = None
    ) -> Dict[str, LLMResponse]:
        """
        Query multiple models in parallel and compare responses.
        
        Useful for testing which model works best for your use case.
        """
        if providers is None:
            providers = list(self.clients.keys())
        
        system_prompt = "You are a helpful AI assistant."
        
        # Query all in parallel
        tasks = []
        for provider in providers:
            client = self.clients.get(provider)
            if client and await client.health_check():
                tasks.append((provider.value, client.generate(system_prompt, prompt)))
        
        results = {}
        for name, task in tasks:
            try:
                response = await task
                results[name] = response
            except Exception as e:
                results[name] = LLMResponse(
                    text=f"Error: {e}",
                    provider=LLMProvider.OLLAMA,
                    model="error",
                    latency_ms=0,
                    cost_estimate=0
                )
        
        return results
    
    def get_provider_stats(self) -> Dict[str, Any]:
        """Get performance statistics for each provider"""
        stats = {}
        for provider in LLMProvider:
            provider_history = [h for h in self.performance_history if h["provider"] == provider.value]
            if provider_history:
                avg_latency = sum(h["latency_ms"] for h in provider_history) / len(provider_history)
                total_cost = sum(h["cost"] for h in provider_history)
                stats[provider.value] = {
                    "queries": len(provider_history),
                    "avg_latency_ms": round(avg_latency, 2),
                    "total_cost_usd": round(total_cost, 4)
                }
        return stats
    
    async def close(self):
        """Close all client sessions"""
        for client in self.clients.values():
            await client.close()
