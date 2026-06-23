import re
import os
from pathlib import Path

SERVER_PATH = r"c:\Users\Aryan\Aryan_Private\myAi\DEEP\interface\server.py"
ROUTERS_DIR = r"c:\Users\Aryan\Aryan_Private\myAi\DEEP\interface\routers"

with open(SERVER_PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

routers = {
    "finance": [], "email": [], "missions": [], "agents": [], "state": [],
    "network": [], "windows": [], "audio": [], "audit": [], "retraining": [],
    "anomaly": [], "science": [], "vision": [], "knowledge": []
}

route_re = re.compile(r'^@app\.(get|post|websocket)\(\"(/ai)?(/api)?(/.*?)(/.*?)?\"')

current_group = None
new_server_lines = []

def get_group(path):
    if '/finance' in path: return 'finance'
    if '/email' in path: return 'email'
    if '/mission' in path: return 'missions'
    if '/agent' in path or '/plugin' in path: return 'agents'
    if '/state' in path: return 'state'
    if '/network' in path or '/investigate' in path: return 'network'
    if '/windows' in path: return 'windows'
    if '/audio' in path: return 'audio'
    if '/audit' in path: return 'audit'
    if '/retraining' in path: return 'retraining'
    if '/anomaly' in path: return 'anomaly'
    if '/math/' in path or '/science/' in path: return 'science'
    if '/vision' in path: return 'vision'
    if '/knowledge' in path: return 'knowledge'
    return None

skip = False
for line in lines:
    m = route_re.match(line)
    if m:
        # the path could be in group 3 or group 4
        # match structure: group 1 is get/post, group 2 is /ai, group 3 is /api, group 4 is the first path segment
        # Actually it's better to just check the whole string match
        path_start = m.group(0)
        group = get_group(path_start)
        
        # some exact matches
        if '"/actions_' in line or '"/get_pending_interactive' in line or '"/respond_to_interactive' in line:
            group = 'security' # ignore for now
        
        if group in routers:
            current_group = group
            routers[group].append(line.replace('@app.', f'@router.'))
            skip = True
        else:
            new_server_lines.append(line)
            skip = False
            current_group = None
    elif skip:
        if line.startswith('@app.') or (line.startswith('def ') and not line.startswith('    ')):
            pass
        
        if not line.startswith(' ') and not line.startswith('@') and line.strip() != '' and not line.startswith('def ') and not line.startswith('async def '):
            current_group = None
            skip = False
            new_server_lines.append(line)
            continue
        
        if current_group:
            routers[current_group].append(line)
    else:
        new_server_lines.append(line)

# For finance, email, etc., we need to make sure we grab the initial imports like `_finance_api = PersonalFinanceEngine()`
# Those weren't inside the route but right above.
# The script above misses them.

