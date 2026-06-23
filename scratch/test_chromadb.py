import sys
import asyncio
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.ltm_memory import LongTermMemory

def test_chroma():
    print("Initializing LongTermMemory...")
    ltm = LongTermMemory()
    
    if ltm._chroma_client is None:
        print("ERROR: ChromaDB client failed to initialize.")
        return
        
    print("SUCCESS: ChromaDB is active!")
    
    # Store a test memory
    memory_id = ltm.store("fact", "Aryan's favorite color is cyberpunk neon blue.", importance=2.0)
    print(f"Stored memory with ID: {memory_id}")
    
    # Recall the memory
    results = ltm.recall("What is my favorite color?")
    print(f"Recalled {len(results)} results.")
    
    for r in results:
        print(f" - [{r.importance}] {r.content}")

if __name__ == "__main__":
    test_chroma()
