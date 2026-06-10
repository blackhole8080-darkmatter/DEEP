# deep/files.py — File & Folder Management (Bible Section 26.2)
"""Notes, recursive search, read/write, folder summary, duplicate finder,
archiving. Pure stdlib; chardet optional for encoding detection."""
from __future__ import annotations

import fnmatch
import hashlib
import os
import time
import zipfile
from datetime import datetime

try:
    from . import config
    NOTES_DIR = str(config.NOTES_DIR)
except Exception:  # pragma: no cover
    NOTES_DIR = os.path.join(os.path.expanduser("~"), "deep_output", "notes")

os.makedirs(NOTES_DIR, exist_ok=True)


class FileManager:
    def __init__(self, config=None):
        self.config = config

    def save_note(self, text: str, title: str = None) -> dict:
        title = title or f"note_{int(time.time())}"
        path = os.path.join(NOTES_DIR, f"{title}.md")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n## {datetime.now():%Y-%m-%d %H:%M}\n{text}\n")
        return {"path": path, "result": path,
                "verbal": f"Noted, sir. Saved to {os.path.basename(path)}."}

    def search_files(self, query, path=None, file_type=None) -> dict:
        root = path or os.path.expanduser("~")
        results = []
        for dirpath, _, files in os.walk(root):
            if dirpath.count(os.sep) - root.count(os.sep) > 4:
                continue
            for fn in files:
                if fnmatch.fnmatch(fn.lower(), f"*{query.lower()}*") and \
                        (not file_type or fn.endswith(file_type)):
                    fp = os.path.join(dirpath, fn)
                    try:
                        st = os.stat(fp)
                        results.append({"path": fp, "size": st.st_size,
                                        "modified": st.st_mtime})
                    except Exception:
                        pass
                    if len(results) >= 50:
                        break
            if len(results) >= 50:
                break
        return {"results": results, "result": len(results),
                "verbal": f"Found {len(results)} file(s) matching '{query}', sir."}

    def read_file(self, path, lines=None) -> dict:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        all_lines = content.splitlines()
        if lines:
            content = "\n".join(all_lines[lines[0]-1:lines[1]])
        return {"content": content, "line_count": len(all_lines),
                "size_kb": round(len(content)/1024, 1), "result": content[:200],
                "verbal": f"Read {len(all_lines)} lines from {os.path.basename(path)}, sir."}

    def write_file(self, path, content, mode="overwrite") -> dict:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        backup = None
        if mode == "overwrite" and os.path.exists(path):
            backup = path + ".bak"
            try:
                os.replace(path, backup)
            except Exception:
                backup = None
        with open(path, "a" if mode == "append" else "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "backup_path": backup, "result": path,
                "verbal": f"Wrote {len(content)} chars to {os.path.basename(path)}, sir."}

    def summarise_folder(self, path, depth=2) -> dict:
        total = 0; counts = {}; largest = []
        for dirpath, _, files in os.walk(path):
            for fn in files:
                fp = os.path.join(dirpath, fn)
                try:
                    sz = os.path.getsize(fp); total += sz
                    ext = os.path.splitext(fn)[1] or "(none)"
                    counts[ext] = counts.get(ext, 0) + 1
                    largest.append((sz, fp))
                except Exception:
                    pass
        largest.sort(reverse=True)
        return {"total_size_mb": round(total/1e6, 1), "file_counts": counts,
                "largest": [{"path": p, "mb": round(s/1e6, 2)} for s, p in largest[:5]],
                "result": {"total_mb": round(total/1e6, 1)},
                "verbal": f"{path}: {sum(counts.values())} files, "
                          f"{total/1e6:.1f} MB total, sir."}

    def find_duplicates(self, path) -> dict:
        hashes = {}
        for dirpath, _, files in os.walk(path):
            for fn in files:
                fp = os.path.join(dirpath, fn)
                try:
                    h = hashlib.md5(open(fp, "rb").read()).hexdigest()
                    hashes.setdefault(h, []).append(fp)
                except Exception:
                    pass
        dups = {h: ps for h, ps in hashes.items() if len(ps) > 1}
        return {"duplicate_groups": list(dups.values()), "result": len(dups),
                "verbal": f"Found {len(dups)} group(s) of duplicate files, sir."}

    def archive_folder(self, path, output=None) -> dict:
        output = output or path.rstrip("/\\") + ".zip"
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
            for dirpath, _, files in os.walk(path):
                for fn in files:
                    fp = os.path.join(dirpath, fn)
                    z.write(fp, os.path.relpath(fp, path))
        return {"archive_path": output, "result": output,
                "verbal": f"Archived to {os.path.basename(output)}, sir."}

    def test(self) -> None:
        n = self.save_note("test note from DEEP")
        assert os.path.exists(n["path"])
        r = self.read_file(n["path"])
        assert "test note" in r["content"]
        print("files.FileManager: OK")


_engine = FileManager()


def save_note(text: str) -> dict:
    import re
    payload = re.sub(r"^.*?(note|remember this|write down|save that)\b[:,]?\s*",
                     "", text, flags=re.I).strip() or text
    return _engine.save_note(payload)


def test() -> None:
    FileManager().test()


if __name__ == "__main__":
    test()
