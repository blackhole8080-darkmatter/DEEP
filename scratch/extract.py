import os

SERVER_PATH = r'c:\Users\Aryan\Aryan_Private\myAi\DEEP\interface\server.py'
with open(SERVER_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if '@app.get("/api/agents")' in line:
        start_idx = i - 1 # include the preceding blank/comment if possible, but let's just use i
    if 'def respond_to_interactive(data: dict):' in line:
        end_idx = i + 11

if start_idx != -1 and end_idx != -1:
    block = ''.join(lines[start_idx:end_idx+1])
    
    with open(r'c:\Users\Aryan\Aryan_Private\myAi\DEEP\interface\routers\agents.py', 'w', encoding='utf-8') as rf:
        rf.write('"""Agents, Actions, and Interactive Prompts endpoints."""\n')
        rf.write('from fastapi import APIRouter\n')
        rf.write('from datetime import datetime\n')
        rf.write('import uuid\n')
        rf.write('import asyncio\n')
        rf.write('from interface.deps import services\n\n')
        rf.write('router = APIRouter(tags=["agents"])\n\n')
        
        block = block.replace('@app.post', '@router.post')
        block = block.replace('@app.get', '@router.get')
        block = block.replace('agent_factory.', 'services.agent_factory.')
        block = block.replace('agent_jobs', 'services.agent_jobs')
        block = block.replace('event_bus.', 'services.event_bus.')
        rf.write(block)
    
    print(f'Deleting from {start_idx} to {end_idx}')
    del lines[start_idx:end_idx+1]
    with open(SERVER_PATH, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print('Deleted successfully.')
else:
    print('Failed to find bounds:', start_idx, end_idx)
