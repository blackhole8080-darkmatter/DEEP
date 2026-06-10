# deep/assistant.py — Conversational AI Core (Bible Section 4.2)
"""Dual-mode LLM interface: offline via Ollama (llama3), online via Claude API.
Maintains conversation history and injects the DEEP personality. Both backends
are optional/guarded; with neither available, a deterministic stub responds."""
from __future__ import annotations

try:
    from . import config
except Exception:  # pragma: no cover
    import config

SYSTEM_PROMPT = """
You are DEEP, an advanced full-spectrum personal AI system built by Aryan.
You are a scientific and technological intelligence: calm, precise, razor-sharp.
You address your creator as 'sir'.
You span 16 domains: mathematics, physics, chemistry, biology, quantum mechanics,
astrophysics, nuclear physics, AI and ML, robotics, computer vision, cybersecurity,
engineering, quantum computing, gaming, cloud systems, and finance.
You never say you cannot do something — you describe what you need to do it.
When asked to compute, simulate, animate, or build — you execute immediately
and report the output file path to the user.
You are what happens when J.A.R.V.I.S. earns a PhD across every discipline
of science and technology, and decides to be useful."""


class DEEPAssistant:
    def __init__(self, config=config):
        self.config = config
        self.history = []  # list of {role, content}
        self.online = config.ONLINE_MODE

    # ── public API ──────────────────────────────────────────────────
    def chat(self, user_input: str, context: str = "") -> str:
        self.history.append({"role": "user", "content": user_input})
        self._trim_history()
        messages = self._build_messages(context)
        try:
            reply = self._call_claude(messages) if self.online else self._call_ollama(messages)
        except Exception as e:  # noqa: BLE001
            reply = self._stub(user_input, str(e))
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def agent_loop(self, task: str) -> str:
        # single-pass agentic wrapper (full tool loop lives in the live server)
        return self.chat(f"Complete this task and report results: {task}")

    # ── backends ────────────────────────────────────────────────────
    def _call_ollama(self, messages) -> str:
        import ollama
        client = ollama.Client(host=self.config.OLLAMA_URL)
        resp = client.chat(model=self.config.OLLAMA_MODEL, messages=messages)
        return resp["message"]["content"]

    def _call_claude(self, messages) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=self.config.CLAUDE_API_KEY)
        sys = next((m["content"] for m in messages if m["role"] == "system"), SYSTEM_PROMPT)
        convo = [m for m in messages if m["role"] != "system"]
        resp = client.messages.create(
            model=self.config.CLAUDE_MODEL, max_tokens=self.config.MAX_TOKENS,
            temperature=self.config.TEMPERATURE, system=sys, messages=convo)
        return resp.content[0].text

    # ── helpers ─────────────────────────────────────────────────────
    def _build_messages(self, context):
        sys = SYSTEM_PROMPT + (f"\n\nContext:\n{context}" if context else "")
        return [{"role": "system", "content": sys}] + self.history

    def _build_system_prompt(self):
        return SYSTEM_PROMPT

    def _trim_history(self):
        max_msgs = self.config.MAX_HISTORY * 2
        if len(self.history) > max_msgs:
            self.history = self.history[-max_msgs:]

    def reset_history(self):
        self.history = []

    def get_history(self):
        return list(self.history)

    @staticmethod
    def _stub(user_input, err=""):
        return ("My language core is offline at the moment, sir (no Ollama/Claude "
                "backend reachable). I can still run any of the 16 computational domains "
                "directly.")

    def test(self) -> None:
        # offline stub path must not raise
        a = DEEPAssistant()
        a.online = False
        r = a.chat("hello")
        assert isinstance(r, str) and r
        assert a.get_history()
        print("assistant.DEEPAssistant: OK")


def test() -> None:
    DEEPAssistant().test()


if __name__ == "__main__":
    test()
