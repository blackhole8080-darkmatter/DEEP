# deep/home_control.py — Smart Home (Bible Section 1: Home Assistant REST API)
"""Control smart-home devices via the Home Assistant REST API. Requires
HA_URL + HA_TOKEN in the environment; otherwise reports gracefully."""
from __future__ import annotations

import os
import re


class HomeControl:
    def __init__(self, config=None):
        self.config = config
        self.ha_url = os.getenv("HA_URL", "http://localhost:8123")
        self.ha_token = os.getenv("HA_TOKEN")

    def _headers(self):
        return {"Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json"}

    def call_service(self, domain, service, entity_id, data=None) -> dict:
        if not self.ha_token:
            return {"result": None,
                    "verbal": "Home Assistant isn't configured, sir (set HA_TOKEN). "
                              f"Would call {domain}.{service} on {entity_id}."}
        try:
            import requests
            payload = {"entity_id": entity_id, **(data or {})}
            r = requests.post(f"{self.ha_url}/api/services/{domain}/{service}",
                              json=payload, headers=self._headers(), timeout=8)
            ok = r.status_code in (200, 201)
            return {"result": ok,
                    "verbal": f"{'Done' if ok else 'Failed'}: {service} {entity_id}, sir."}
        except Exception as e:  # noqa: BLE001
            return {"result": None, "verbal": f"Home Assistant call failed, sir: {e}"}

    def turn_on(self, entity_id, brightness=None):
        data = {"brightness": brightness} if brightness else None
        return self.call_service(entity_id.split(".")[0], "turn_on", entity_id, data)

    def turn_off(self, entity_id):
        return self.call_service(entity_id.split(".")[0], "turn_off", entity_id)

    def test(self) -> None:
        # without token, must return a graceful dict
        r = self.turn_on("light.living_room")
        assert isinstance(r, dict) and "verbal" in r
        print("home_control.HomeControl: OK")


_engine = HomeControl()


def execute(text: str) -> dict:
    low = text.lower()
    action = "turn_off" if ("off" in low or "turn off" in low) else "turn_on"
    # crude entity inference
    entity = "light.living_room"
    if "thermostat" in low or "temperature" in low:
        entity = "climate.home"
    elif "fan" in low:
        entity = "fan.bedroom"
    m = re.search(r"(\d+)\s*%?\s*bright", low)
    bright = int(int(m.group(1)) * 2.55) if m else None
    if action == "turn_on":
        return _engine.turn_on(entity, bright)
    return _engine.turn_off(entity)


def test() -> None:
    HomeControl().test()


if __name__ == "__main__":
    test()
