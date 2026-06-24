import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.agent_factory import AgentFactory
from core.tools.deep_registry import DeepToolRegistry
from core.event_bus import EventBus

# Mock LLM and Agent
class MockLLM:
    async def generate(self, *args, **kwargs):
        await asyncio.sleep(2)
        return "I found the answer!"

async def test_agent_decoupling():
    event_bus = EventBus()
    tools = DeepToolRegistry()
    factory = AgentFactory(MockLLM(), tools, event_bus)
    
    # We will track events
    events = []
    async def on_event(event, payload):
        print(f"EVENT: {event} -> {payload}")
        events.append(event)
    
    event_bus.subscribe("agent_task_start", lambda p: on_event("start", p))
    event_bus.subscribe("agent_task_complete", lambda p: on_event("complete", p))
    
    factory.create_agent("TestBot", "researcher")
    
    print("Assigning task...")
    result = await factory.assign_task("TestBot", "Solve a hard math problem")
    print("assign_task returned immediately with:", result)
    
    assert result["status"] == "queued"
    
    print("Waiting for background task to finish...")
    await asyncio.sleep(3)
    
    assert "complete" in events
    print("SUCCESS: Sub-Agent decoupled correctly!")

if __name__ == "__main__":
    asyncio.run(test_agent_decoupling())
