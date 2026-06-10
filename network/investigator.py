"""
network/investigator.py — turn an unknown identifier into a dossier.

Given an IP, MAC, hostname or domain, DEEP gathers what it can WITHOUT touching
the target aggressively: classification, reverse-DNS, MAC vendor (OUI),
private/public, and geolocation/ISP for public IPs (ip-api.com, free, no key).
Pure-stdlib + one optional HTTP lookup; offline-safe.
"""
from __future__ import annotations

import ipaddress
import re
import socket
from typing import Any

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore

from network.enrich import mac_vendor

_MAC_RE = re.compile(r"^([0-9a-f]{2}[:-]){5}[0-9a-f]{2}$", re.IGNORECASE)
_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def classify(target: str) -> str:
    t = (target or "").strip()
    if _MAC_RE.match(t):
        return "mac"
    if _IP_RE.match(t):
        return "ip"
    if "." in t:
        return "host"
    return "unknown"


def _reverse_dns(ip: str) -> str | None:
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return None


def _geo(ip: str) -> dict[str, Any] | None:
    if requests is None:
        return None
    try:
        r = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,country,regionName,city,isp,org,as,lat,lon,reverse,mobile,proxy,hosting"},
            timeout=5,
        )
        d = r.json()
        if d.get("status") == "success":
            return d
    except Exception:
        return None
    return None


def investigate(target: str) -> dict[str, Any]:
    kind = classify(target)
    dossier: dict[str, Any] = {"target": target, "kind": kind, "findings": []}

    def add(label: str, value: Any):
        if value not in (None, "", []):
            dossier["findings"].append({"label": label, "value": value})

    if kind == "mac":
        vendor = mac_vendor(target)
        randomized = False
        try:
            randomized = bool(int(target.replace(":", "").replace("-", "")[1], 16) & 0x2)
        except Exception:
            pass
        dossier["vendor"] = vendor
        dossier["randomized"] = randomized
        add("Vendor (OUI)", vendor or "unknown")
        add("Address type", "randomized / private MAC" if randomized else "globally-unique (real hardware)")
        dossier["summary"] = (
            f"{vendor} device" if vendor else
            ("Privacy-randomized MAC (phone/laptop hiding its identity)" if randomized else "Unknown-vendor device")
        )
        return dossier

    ip = target
    if kind == "host":
        try:
            ip = socket.gethostbyname(target)
            add("Resolved IP", ip)
        except Exception:
            dossier["summary"] = "Could not resolve hostname."
            return dossier

    if kind in ("ip", "host"):
        try:
            ipobj = ipaddress.ip_address(ip)
            is_private = ipobj.is_private
        except Exception:
            is_private = False
            ipobj = None
        dossier["ip"] = ip
        dossier["private"] = is_private
        rdns = _reverse_dns(ip)
        add("Reverse DNS", rdns)
        add("Scope", "private / LAN" if is_private else "public / internet")

        if is_private:
            dossier["summary"] = f"Local network host {ip}" + (f" ({rdns})" if rdns else "")
        else:
            geo = _geo(ip)
            if geo:
                loc = ", ".join(x for x in (geo.get("city"), geo.get("regionName"), geo.get("country")) if x)
                add("Location", loc)
                add("ISP / Org", geo.get("isp") or geo.get("org"))
                add("Network (AS)", geo.get("as"))
                flags = [k for k in ("mobile", "proxy", "hosting") if geo.get(k)]
                if flags:
                    add("Flags", ", ".join(flags))
                dossier["geo"] = {k: geo.get(k) for k in ("country", "regionName", "city", "isp", "org", "as", "lat", "lon")}
                risk = "elevated" if geo.get("proxy") or geo.get("hosting") else "normal"
                dossier["risk"] = risk
                dossier["summary"] = f"Public host in {loc or 'unknown location'} — {geo.get('isp') or geo.get('org') or 'unknown ISP'}" + (f" (⚠ {', '.join(flags)})" if flags else "")
            else:
                dossier["summary"] = f"Public IP {ip}" + (f" ({rdns})" if rdns else "")
        return dossier

    dossier["summary"] = "Unrecognized target. Provide an IP, MAC, hostname or domain."
    return dossier
