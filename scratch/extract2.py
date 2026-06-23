import os

SERVER_PATH = r'c:\Users\Aryan\Aryan_Private\myAi\DEEP\interface\server.py'
with open(SERVER_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

def extract_block(start_marker, end_marker, router_name, tags, deps_replacements):
    start_idx, end_idx = -1, -1
    for i, line in enumerate(lines):
        if start_marker in line: start_idx = i - 1
        if end_marker in line: end_idx = i + 15
    
    # refine end index to actual end of function
    if start_idx != -1 and end_idx != -1:
        while end_idx < len(lines) and (lines[end_idx].strip() == '' or lines[end_idx].startswith(' ')):
            end_idx += 1
        end_idx -= 1
        
        block = ''.join(lines[start_idx:end_idx+1])
        
        out_path = rf'c:\Users\Aryan\Aryan_Private\myAi\DEEP\interface\routers\{router_name}.py'
        with open(out_path, 'w', encoding='utf-8') as rf:
            rf.write(f'"""{router_name.capitalize()} endpoints."""\n')
            rf.write('from fastapi import APIRouter\n')
            rf.write('from typing import Optional\n')
            rf.write('from interface.deps import services\n\n')
            rf.write(f'router = APIRouter(tags={tags})\n\n')
            
            block = block.replace('@app.post', '@router.post')
            block = block.replace('@app.get', '@router.get')
            for old, new in deps_replacements.items():
                block = block.replace(old, new)
            rf.write(block)
        
        for i in range(start_idx, end_idx+1):
            lines[i] = '\n'
        print(f'Extracted {router_name}')
    else:
        print(f'Failed to find {router_name}')

extract_block('@app.get("/audit/log")', 'def audit_export_session(session_id: str', 'audit', '["audit"]', {'audit.': 'services.audit_trail.'})
extract_block('@app.get("/ai/retraining/status")', 'def retraining_history()', 'ai', '["ai"]', {'retraining_scheduler.': 'services.retraining_scheduler.'})

with open(SERVER_PATH, 'w', encoding='utf-8') as f:
    f.writelines([line for line in lines if line != '\n\n\n\n\n'])
print('Done.')
