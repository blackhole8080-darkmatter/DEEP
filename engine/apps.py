# deep/apps.py — Application Control (Bible Section 26.4)
"""Launch apps, screenshots, OCR, clipboard, reminders. Heavy GUI libs
(pyautogui, mss, pytesseract, pyperclip) are optional/guarded."""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime, timedelta

try:
    from . import config
    SHOT_DIR = os.path.join(str(config.BASE_DIR), "screenshots")
except Exception:  # pragma: no cover
    SHOT_DIR = os.path.join(os.path.expanduser("~"), "deep_output", "screenshots")
os.makedirs(SHOT_DIR, exist_ok=True)

APP_ALIASES = {
    "chrome": "chrome", "browser": "chrome", "vscode": "code", "code": "code",
    "notepad": "notepad", "calculator": "calc", "calc": "calc",
    "explorer": "explorer", "terminal": "cmd", "spotify": "spotify",
}


class AppController:
    def __init__(self, config=None):
        self.config = config
        self._reminders = []

    def launch_app(self, name) -> dict:
        exe = APP_ALIASES.get(name.lower(), name)
        try:
            if platform.system() == "Windows":
                if exe in ("calc", "notepad", "explorer", "cmd"):
                    subprocess.Popen(exe, shell=True)
                else:
                    path = shutil.which(exe) or exe
                    subprocess.Popen([path], shell=True)
            else:
                subprocess.Popen([shutil.which(exe) or exe])
            return {"result": True, "verbal": f"Launching {name}, sir."}
        except Exception as e:  # noqa: BLE001
            return {"result": None, "verbal": f"Could not launch {name}, sir: {e}"}

    def take_screenshot(self, output=None) -> dict:
        path = output or os.path.join(SHOT_DIR, f"shot_{int(time.time())}.png")
        try:
            import mss
            with mss.mss() as sct:
                sct.shot(output=path)
            return {"image_path": path, "result": path,
                    "verbal": f"Screenshot saved to {os.path.basename(path)}, sir."}
        except Exception:
            try:
                import pyautogui
                pyautogui.screenshot(path)
                return {"image_path": path, "result": path,
                        "verbal": f"Screenshot saved, sir."}
            except Exception as e:  # noqa: BLE001
                return {"result": None, "verbal": f"Screenshot needs mss/pyautogui, sir: {e}"}

    def ocr_screen(self) -> dict:
        try:
            import pytesseract
            from PIL import Image
            shot = self.take_screenshot()
            if not shot.get("image_path"):
                return shot
            txt = pytesseract.image_to_string(Image.open(shot["image_path"]))
            return {"text": txt, "result": txt[:200],
                    "verbal": f"Read {len(txt)} characters from screen, sir."}
        except Exception as e:  # noqa: BLE001
            return {"result": None, "verbal": f"OCR needs pytesseract + tesseract, sir: {e}"}

    def clipboard_read(self) -> dict:
        try:
            import pyperclip
            return {"content": pyperclip.paste(), "result": pyperclip.paste(),
                    "verbal": "Read clipboard, sir."}
        except Exception:
            return {"result": None, "verbal": "pyperclip not installed, sir."}

    def clipboard_write(self, content) -> dict:
        try:
            import pyperclip
            pyperclip.copy(content)
            return {"result": True, "verbal": "Copied to clipboard, sir."}
        except Exception:
            return {"result": None, "verbal": "pyperclip not installed, sir."}

    def set_reminder(self, message, delay_seconds=None, at_time=None) -> dict:
        if at_time and not delay_seconds:
            try:
                hh, mm = map(int, at_time.split(":"))
                now = datetime.now()
                target = now.replace(hour=hh, minute=mm, second=0)
                if target < now:
                    target += timedelta(days=1)
                delay_seconds = (target - now).total_seconds()
            except Exception:
                delay_seconds = 60
        delay_seconds = delay_seconds or 60

        def fire():
            time.sleep(delay_seconds)
            print(f"[DEEP REMINDER] {message}")
        t = threading.Thread(target=fire, daemon=True); t.start()
        self._reminders.append(message)
        fire_at = datetime.now() + timedelta(seconds=delay_seconds)
        return {"scheduled_for": fire_at.isoformat(), "result": message,
                "verbal": f"Reminder set for {fire_at:%H:%M}, sir: {message}"}

    def test(self) -> None:
        r = self.set_reminder("test", delay_seconds=3600)
        assert r["result"] == "test"
        print("apps.AppController: OK")


_engine = AppController()


def launch(text: str) -> dict:
    m = re.search(r"(?:open|launch|run|start)\s+(?:app\s+|program\s+)?(\w+)", text, re.I)
    return _engine.launch_app(m.group(1) if m else text.split()[-1])


def screenshot(text: str) -> dict:
    return _engine.take_screenshot()


def reminder(text: str) -> dict:
    at = re.search(r"\b(\d{1,2}:\d{2})\b", text)
    secs = re.search(r"in\s+(\d+)\s*(second|minute|hour)", text, re.I)
    msg = re.sub(r"^.*?(remind me|set alarm|timer)\b[:,]?\s*", "", text, flags=re.I).strip()
    delay = None
    if secs:
        n = int(secs.group(1))
        mult = {"second": 1, "minute": 60, "hour": 3600}[secs.group(2).lower()]
        delay = n * mult
    return _engine.set_reminder(msg or "reminder", delay_seconds=delay,
                                at_time=at.group(1) if at else None)


def test() -> None:
    AppController().test()


if __name__ == "__main__":
    test()
