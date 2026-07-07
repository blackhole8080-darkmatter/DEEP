import os
import re

files_to_delete = [
    '/workspaces/DEEP/interface/routers/agents.py',
    '/workspaces/DEEP/interface/routers/research.py',
    '/workspaces/DEEP/interface/routers/missions.py',
    '/workspaces/DEEP/interface/routers/system.py',
    '/workspaces/DEEP/interface/routers/email.py',
    '/workspaces/DEEP/interface/routers/finance.py',
    '/workspaces/DEEP/core/research_engine.py',
    '/workspaces/DEEP/core/agent_factory.py',
    '/workspaces/DEEP/ai/agent_swarm.py'
]

for f in files_to_delete:
    if os.path.exists(f):
        os.remove(f)
        print(f"Deleted {f}")

# Clean server.py
with open('/workspaces/DEEP/interface/server.py', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if 'agent_swarm = AgentSwarm(' in line:
        skip = True
    if skip:
        if ')' in line:
            skip = False
        continue
    
    # Exclude any line importing or calling these
    if any(x in line for x in [
        'AgentFactory', 'ResearchEngine', 'AgentSwarm', 
        'research_engine', 'agent_factory', 'agent_swarm'
    ]):
        continue
    new_lines.append(line)

with open('/workspaces/DEEP/interface/server.py', 'w') as f:
    f.writelines(new_lines)

print("Cleaned server.py")

# Clean interface/deps.py
with open('/workspaces/DEEP/interface/deps.py', 'r') as f:
    lines = f.readlines()
new_lines = []
for line in lines:
    if any(x in line for x in ['research_engine', 'agent_factory', 'agent_swarm']):
        continue
    new_lines.append(line)
with open('/workspaces/DEEP/interface/deps.py', 'w') as f:
    f.writelines(new_lines)

# Also remove references in core/tools/legacy.py
with open('/workspaces/DEEP/core/tools/legacy.py', 'r') as f:
    content = f.read()

# We just remove the blocks that use agent_factory and agent_swarm
content = re.sub(r"elif tool_name == 'agent_create':.*?elif tool_name == 'ask_options':", r"elif tool_name == 'ask_options':", content, flags=re.DOTALL)
with open('/workspaces/DEEP/core/tools/legacy.py', 'w') as f:
    f.write(content)

print("Cleaned legacy.py")
