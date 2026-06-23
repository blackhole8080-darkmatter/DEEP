import os

SERVER_PATH = r'c:\Users\Aryan\Aryan_Private\myAi\DEEP\interface\server.py'
with open(SERVER_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if 'def build_jarvis_context(ws_id: int, user_input: str) -> str:' in line:
        start_idx = i - 10 # includes time_of_day and session_history dict
    if 'async def handle_voice(ws: WebSocket, msg: dict):' in line:
        end_idx = i - 2 # up to the fallback handler

if start_idx != -1 and end_idx != -1:
    block = ''.join(lines[start_idx:end_idx+1])
    
    with open(r'c:\Users\Aryan\Aryan_Private\myAi\DEEP\scratch\chat_block.py', 'w', encoding='utf-8') as rf:
        rf.write(block)
    print("Exported chat block to scratch/chat_block.py")
else:
    print("Failed to find bounds")
