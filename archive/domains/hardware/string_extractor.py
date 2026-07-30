"""
DEEP — String Extractor
Extracts printable strings from binary files with categorization.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ExtractedString:
    offset: int
    value: str
    category: str   # "credential" | "url" | "ip" | "path" | "email" | "version" | "generic"
    risk_level: str # "HIGH" | "MEDIUM" | "LOW" | "INFO"


_CATEGORIES = [
    ("credential", re.compile(r"(password|passwd|pwd|secret|token|apikey|api_key)[=:\s]+\S+", re.I), "HIGH"),
    ("url",        re.compile(r"https?://[\w./:%?&=@#-]{8,}"), "INFO"),
    ("ip",         re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?\b"), "LOW"),
    ("email",      re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "LOW"),
    ("path",       re.compile(r"(?:/[a-z][a-z0-9_/-]{2,}){2,}"), "LOW"),
    ("version",    re.compile(r"v?\d+\.\d+(\.\d+)?(-\w+)?"), "INFO"),
    ("private_key", re.compile(r"-----BEGIN .* PRIVATE KEY-----"), "HIGH"),
    ("certificate", re.compile(r"-----BEGIN CERTIFICATE-----"), "INFO"),
]


class StringExtractor:
    def extract(self, data: bytes, min_len: int = 6) -> List[ExtractedString]:
        """Extract and categorize printable strings from binary data."""
        results = []
        pattern = re.compile(rb"[ -~]{" + str(min_len).encode() + rb",}")

        for match in pattern.finditer(data):
            s = match.group().decode(errors="replace")
            offset = match.start()
            category = "generic"
            risk = "INFO"

            for cat, cat_pattern, cat_risk in _CATEGORIES:
                if cat_pattern.search(s):
                    category = cat
                    risk = cat_risk
                    break

            results.append(ExtractedString(offset=offset, value=s, category=category, risk_level=risk))

        return results
