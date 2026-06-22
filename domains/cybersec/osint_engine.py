"""
DEEP — OSINT Engine
Passive reconnaissance: WHOIS, RDAP, cert transparency, DNS, Shodan, metadata.
All queries are PASSIVE — no active probing of targets.
"""
from __future__ import annotations

import asyncio
import json
import re
import socket
import struct
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlencode, quote

try:
    import aiohttp
    _AIOHTTP_OK = True
except ImportError:
    _AIOHTTP_OK = False

try:
    import dns.resolver
    import dns.rdatatype
    _DNSPYTHON_OK = True
except ImportError:
    _DNSPYTHON_OK = False


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class DNSRecord:
    type: str       # A, AAAA, MX, TXT, NS, CNAME, etc.
    value: str
    ttl: int = 0


@dataclass
class Certificate:
    id: int
    issuer: str
    common_name: str
    name_value: str     # may contain SANs (newline-delimited)
    not_before: str
    not_after: str
    serial_number: str = ""


@dataclass
class GeoInfo:
    ip: str
    country: str
    country_code: str
    region: str
    city: str
    isp: str
    asn: str
    org: str
    lat: float = 0.0
    lon: float = 0.0


@dataclass
class ShodanRecord:
    ip: str
    ports: List[int]
    hostnames: List[str]
    country: str
    org: str
    isp: str
    os: Optional[str]
    vulns: List[str]
    banners: Dict[int, str] = field(default_factory=dict)


@dataclass
class MetadataReport:
    file_path: str
    file_type: str
    author: Optional[str] = None
    creator_tool: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    gps_alt: Optional[float] = None
    revision_count: Optional[int] = None
    embedded_paths: List[str] = field(default_factory=list)
    suspicious_indicators: List[str] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OSINTReport:
    target: str
    target_type: str            # "domain" | "ip" | "email"
    dns_records: List[DNSRecord] = field(default_factory=list)
    certificates: List[Certificate] = field(default_factory=list)
    geo_info: Optional[GeoInfo] = None
    whois_raw: str = ""
    subdomains: List[str] = field(default_factory=list)
    open_ports: List[int] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    risk_indicators: List[str] = field(default_factory=list)
    summary: str = ""


# ── OSINT Engine ──────────────────────────────────────────────────────────────

class OSINTEngine:
    """
    Passive reconnaissance engine.
    Queries public APIs only — no active probing of targets.
    """

    def __init__(self, shodan_key: Optional[str] = None, vt_key: Optional[str] = None):
        self._shodan_key = shodan_key
        self._vt_key = vt_key

    # ── Public API ─────────────────────────────────────────────────────────────

    async def passive_recon(self, target: str) -> OSINTReport:
        """
        Full passive reconnaissance.
        target: domain name, IP address, or email.
        """
        # Determine type
        target = target.strip().lower()
        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", target):
            t_type = "ip"
        elif "@" in target:
            t_type = "email"
        else:
            t_type = "domain"

        report = OSINTReport(target=target, target_type=t_type)

        # Run queries in parallel
        tasks = []
        if t_type in ("domain", "email"):
            domain = target.split("@")[-1] if t_type == "email" else target
            tasks.append(self._query_dns(domain, report))
            tasks.append(self._query_cert_transparency(domain, report))
            tasks.append(self._query_geo(domain, report))
        elif t_type == "ip":
            tasks.append(self._query_geo(target, report))
            if self._shodan_key:
                tasks.append(self._query_shodan(target, report))

        await asyncio.gather(*tasks, return_exceptions=True)
        report.summary = self._build_summary(report)
        return report

    async def extract_metadata(self, file_path: str) -> MetadataReport:
        """
        Extract metadata from documents: PDF, DOCX, images (EXIF).
        """
        report = MetadataReport(file_path=file_path, file_type="unknown")

        try:
            import os
            if not os.path.exists(file_path):
                report.suspicious_indicators.append(f"File not found: {file_path}")
                return report

            ext = os.path.splitext(file_path)[1].lower()
            report.file_type = ext

            if ext == ".pdf":
                await asyncio.to_thread(self._extract_pdf_metadata, file_path, report)
            elif ext in (".jpg", ".jpeg", ".png", ".tiff", ".tif"):
                await asyncio.to_thread(self._extract_exif_metadata, file_path, report)
            elif ext in (".docx", ".xlsx", ".pptx"):
                await asyncio.to_thread(self._extract_ooxml_metadata, file_path, report)
            else:
                report.suspicious_indicators.append(f"Unsupported file type: {ext}")

        except Exception as exc:
            report.suspicious_indicators.append(f"Metadata extraction error: {exc}")

        return report

    async def cert_transparency_search(self, domain: str) -> List[Certificate]:
        """Search crt.sh for certificates issued for a domain."""
        return await self._fetch_crtsh(domain)

    async def shodan_lookup(self, ip: str) -> Optional[ShodanRecord]:
        """Shodan IP lookup (requires SHODAN_API_KEY)."""
        if not self._shodan_key:
            return None
        return await self._query_shodan_raw(ip)

    # ── DNS ───────────────────────────────────────────────────────────────────

    async def _query_dns(self, domain: str, report: OSINTReport) -> None:
        record_types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"]

        if _DNSPYTHON_OK:
            for rtype in record_types:
                try:
                    answers = dns.resolver.resolve(domain, rtype, lifetime=5)
                    for ans in answers:
                        report.dns_records.append(DNSRecord(type=rtype, value=str(ans)))
                except Exception:
                    pass
        else:
            # Fallback: use socket for A records only
            try:
                addrs = socket.getaddrinfo(domain, None)
                for addr in addrs:
                    ip = addr[4][0]
                    rtype = "A" if "." in ip else "AAAA"
                    record = DNSRecord(type=rtype, value=ip)
                    if record not in report.dns_records:
                        report.dns_records.append(record)
            except Exception:
                pass

    # ── Certificate Transparency ──────────────────────────────────────────────

    async def _query_cert_transparency(self, domain: str, report: OSINTReport) -> None:
        certs = await self._fetch_crtsh(domain)
        report.certificates = certs[:20]  # limit

        # Extract unique subdomains from certificate SANs
        subdomains = set()
        for cert in certs:
            for name in cert.name_value.split("\n"):
                name = name.strip().lower()
                if name.endswith(f".{domain}") and "*" not in name:
                    subdomains.add(name)
        report.subdomains = sorted(subdomains)[:50]

    async def _fetch_crtsh(self, domain: str) -> List[Certificate]:
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        certs = []
        try:
            data = await self._get_json(url)
            if isinstance(data, list):
                for entry in data[:50]:
                    certs.append(Certificate(
                        id=entry.get("id", 0),
                        issuer=entry.get("issuer_name", ""),
                        common_name=entry.get("common_name", ""),
                        name_value=entry.get("name_value", ""),
                        not_before=entry.get("not_before", ""),
                        not_after=entry.get("not_after", ""),
                        serial_number=entry.get("serial_number", ""),
                    ))
        except Exception:
            pass
        return certs

    # ── IP Geolocation ────────────────────────────────────────────────────────

    async def _query_geo(self, target: str, report: OSINTReport) -> None:
        try:
            url = f"https://ipapi.co/{target}/json/"
            data = await self._get_json(url)
            if data and "error" not in data:
                report.geo_info = GeoInfo(
                    ip=data.get("ip", target),
                    country=data.get("country_name", ""),
                    country_code=data.get("country_code", ""),
                    region=data.get("region", ""),
                    city=data.get("city", ""),
                    isp=data.get("org", ""),
                    asn=data.get("asn", ""),
                    org=data.get("org", ""),
                    lat=data.get("latitude", 0.0),
                    lon=data.get("longitude", 0.0),
                )
        except Exception:
            pass

    # ── Shodan ────────────────────────────────────────────────────────────────

    async def _query_shodan(self, ip: str, report: OSINTReport) -> None:
        record = await self._query_shodan_raw(ip)
        if record:
            report.open_ports = record.ports
            report.risk_indicators.extend(
                [f"Shodan vuln: {v}" for v in record.vulns]
            )

    async def _query_shodan_raw(self, ip: str) -> Optional[ShodanRecord]:
        if not self._shodan_key:
            return None
        try:
            url = f"https://api.shodan.io/shodan/host/{ip}?key={self._shodan_key}"
            data = await self._get_json(url)
            return ShodanRecord(
                ip=ip,
                ports=data.get("ports", []),
                hostnames=data.get("hostnames", []),
                country=data.get("country_name", ""),
                org=data.get("org", ""),
                isp=data.get("isp", ""),
                os=data.get("os"),
                vulns=list(data.get("vulns", {}).keys()),
                banners={item.get("port", 0): item.get("data", "")[:200]
                         for item in data.get("data", [])},
            )
        except Exception:
            return None

    # ── File metadata extractors ──────────────────────────────────────────────

    def _extract_pdf_metadata(self, path: str, report: MetadataReport) -> None:
        try:
            import pypdf
            with open(path, "rb") as f:
                reader = pypdf.PdfReader(f)
                meta = reader.metadata or {}
            report.raw_metadata = dict(meta)
            report.author = meta.get("/Author")
            report.creator_tool = meta.get("/Creator") or meta.get("/Producer")
            report.creation_date = meta.get("/CreationDate")
            report.modification_date = meta.get("/ModDate")

            # Suspicious indicators
            if meta.get("/Author") == "":
                report.suspicious_indicators.append("Empty author field (sanitized?)")
            if "kali" in str(meta).lower() or "metasploit" in str(meta).lower():
                report.suspicious_indicators.append("⚠ Hacking tool references in metadata")
        except ImportError:
            report.suspicious_indicators.append("pypdf not available — install with pip install pypdf")
        except Exception as exc:
            report.suspicious_indicators.append(f"PDF parse error: {exc}")

    def _extract_exif_metadata(self, path: str, report: MetadataReport) -> None:
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS, GPSTAGS
            img = Image.open(path)
            exif_data = img._getexif() or {}
            report.raw_metadata = {TAGS.get(k, k): str(v) for k, v in exif_data.items()}

            # GPS
            gps_info = None
            for k, v in exif_data.items():
                if TAGS.get(k) == "GPSInfo":
                    gps_info = {GPSTAGS.get(i, i): v[i] for i in v}
                    break

            if gps_info:
                lat = self._convert_gps(gps_info.get("GPSLatitude"), gps_info.get("GPSLatitudeRef", "N"))
                lon = self._convert_gps(gps_info.get("GPSLongitude"), gps_info.get("GPSLongitudeRef", "E"))
                alt = float(gps_info.get("GPSAltitude", 0))
                report.gps_lat = lat
                report.gps_lon = lon
                report.gps_alt = alt
                report.suspicious_indicators.append(
                    f"📍 GPS embedded: {lat:.6f}, {lon:.6f} (alt: {alt:.1f}m)"
                )

            # Software
            software = report.raw_metadata.get("Software", "")
            report.creator_tool = software
        except ImportError:
            report.suspicious_indicators.append("Pillow not available — install with pip install Pillow")
        except Exception as exc:
            report.suspicious_indicators.append(f"EXIF parse error: {exc}")

    def _extract_ooxml_metadata(self, path: str, report: MetadataReport) -> None:
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(path, "r") as z:
                if "docProps/core.xml" in z.namelist():
                    with z.open("docProps/core.xml") as f:
                        tree = ET.parse(f)
                        root = tree.getroot()
                        ns = {
                            "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
                            "dc": "http://purl.org/dc/elements/1.1/",
                            "dcterms": "http://purl.org/dc/terms/",
                        }
                        report.author = (root.find("dc:creator", ns) or type("", (), {"text": None})()).text
                        report.modification_date = (root.find("dcterms:modified", ns) or type("", (), {"text": None})()).text
                        report.creation_date = (root.find("dcterms:created", ns) or type("", (), {"text": None})()).text
                        rev = root.find("cp:revision", ns)
                        if rev is not None and rev.text:
                            report.revision_count = int(rev.text)
        except Exception as exc:
            report.suspicious_indicators.append(f"OOXML parse error: {exc}")

    def _convert_gps(self, coord, ref: str) -> float:
        if not coord:
            return 0.0
        try:
            deg = float(coord[0])
            min_ = float(coord[1])
            sec = float(coord[2])
            val = deg + min_ / 60 + sec / 3600
            if ref in ("S", "W"):
                val = -val
            return val
        except Exception:
            return 0.0

    # ── HTTP helper ───────────────────────────────────────────────────────────

    async def _get_json(self, url: str) -> Any:
        headers = {"User-Agent": "DEEP-ETIS/1.0 (+https://github.com/deep)"}
        if _AIOHTTP_OK:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    return await resp.json(content_type=None)
        else:
            import urllib.request
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())

    # ── Summary builder ───────────────────────────────────────────────────────

    def _build_summary(self, report: OSINTReport) -> str:
        lines = [f"[OSINT] Passive reconnaissance for: {report.target} ({report.target_type})"]

        if report.dns_records:
            a_records = [r.value for r in report.dns_records if r.type == "A"]
            lines.append(f"  DNS A records: {', '.join(a_records[:5])}")

        if report.geo_info:
            g = report.geo_info
            lines.append(f"  Geolocation: {g.city}, {g.country} | ASN: {g.asn} | ISP: {g.isp}")

        if report.subdomains:
            lines.append(f"  Subdomains discovered (crt.sh): {len(report.subdomains)}")

        if report.certificates:
            lines.append(f"  Certificates found: {len(report.certificates)}")

        if report.risk_indicators:
            lines.append(f"  ⚠ Risk indicators: {len(report.risk_indicators)}")
            for ri in report.risk_indicators[:3]:
                lines.append(f"    - {ri}")

        return "\n".join(lines)
