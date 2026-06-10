"""Quick WebSocket smoke test for the DEEP chat path (/ws/deep)."""
import asyncio, json, sys
import websockets

async def main(prompt: str):
    uri = "ws://127.0.0.1:7768/ws/deep"
    async with websockets.connect(uri, max_size=None) as ws:
        await ws.send(json.dumps({"type": "chat", "text": prompt, "mode": "auto"}))
        full = ""
        types_seen = {}
        try:
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=60)
                d = json.loads(raw)
                t = d.get("type", "?")
                types_seen[t] = types_seen.get(t, 0) + 1
                if t == "token":
                    full += d.get("content", "")
                elif t in ("response_end", "done", "complete"):
                    break
                elif t == "error":
                    print("ERROR EVENT:", d); break
        except asyncio.TimeoutError:
            print("[timeout waiting for more messages]")
        print("\n--- EVENT TYPES ---", types_seen)
        print("--- RESPONSE TEXT ---")
        print(full[:1500])

if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "Say hello in one short sentence."
    asyncio.run(main(p))
