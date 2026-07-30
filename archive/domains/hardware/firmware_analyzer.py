"""
DEEP — Firmware Analyzer
Entropy analysis, architecture detection, filesystem carving,
interesting string extraction from binary firmware images.
Pure-Python fallback if binwalk is not installed.
"""
from __future__ import annotations

import asyncio
import binascii
import collections
import math
import os
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np
    _NUMPY_OK = True
except ImportError:
    _NUMPY_OK = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _MPL_OK = True
except ImportError:
    _MPL_OK = False


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class EntropySegment:
    offset: int
    size: int
    entropy: float          # bits per byte (max 8.0)
    segment_type: str       # "compressed" | "encrypted" | "code" | "data" | "padding"
    description: str


@dataclass
class ArchitectureHint:
    arch: str               # "arm32" | "arm64" | "mips" | "x86" | "x86_64" | "riscv" | "unknown"
    endianness: str         # "little" | "big" | "unknown"
    confidence: float
    evidence: str


@dataclass
class FilesystemSignature:
    offset: int
    fs_type: str            # "squashfs" | "jffs2" | "cramfs" | "ext2" | "yaffs" | "romfs"
    description: str
    magic_hex: str


@dataclass
class FirmwareReport:
    file_path: str
    file_size: int
    md5: str
    sha256: str
    architecture: ArchitectureHint
    entropy_segments: List[EntropySegment]
    filesystems: List[FilesystemSignature]
    interesting_strings: List[str]       # URLs, IPs, credentials, version strings
    security_findings: List[str]
    entropy_plot_path: Optional[str] = None
    error: Optional[str] = None


# ── Magic signatures ──────────────────────────────────────────────────────────

_FS_SIGNATURES: List[Dict[str, Any]] = [
    {"magic": b"sqsh", "offset": 0, "fs": "squashfs-le", "desc": "SquashFS (little-endian)"},
    {"magic": b"hsqs", "offset": 0, "fs": "squashfs-be", "desc": "SquashFS (big-endian)"},
    {"magic": b"\x19\x85", "offset": 0, "fs": "jffs2", "desc": "JFFS2 filesystem (little-endian)"},
    {"magic": b"\x85\x19", "offset": 0, "fs": "jffs2-be", "desc": "JFFS2 filesystem (big-endian)"},
    {"magic": b"\x45\x3d\xcd\x28", "offset": 0, "fs": "cramfs", "desc": "Cramfs"},
    {"magic": b"\x28\xcd\x3d\x45", "offset": 0, "fs": "cramfs-be", "desc": "Cramfs (big-endian)"},
    {"magic": b"\x53\xef", "offset": 56, "fs": "ext2/3/4", "desc": "ext2/ext3/ext4 filesystem"},
    {"magic": b"-rom1fs-", "offset": 0, "fs": "romfs", "desc": "ROMFS"},
    {"magic": b"PK\x03\x04", "offset": 0, "fs": "zip/jar", "desc": "ZIP archive (may contain FS)"},
    {"magic": b"\x1f\x8b", "offset": 0, "fs": "gzip", "desc": "GZip compressed data"},
    {"magic": b"BZh", "offset": 0, "fs": "bzip2", "desc": "BZip2 compressed data"},
    {"magic": b"\xfd7zXZ\x00", "offset": 0, "fs": "xz", "desc": "XZ/LZMA2 compressed data"},
    {"magic": b"ustar", "offset": 257, "fs": "tar", "desc": "TAR archive"},
]

# Architecture detection heuristics based on instruction patterns
_ARCH_PATTERNS: Dict[str, Dict[str, Any]] = {
    "arm32-le": {
        "patterns": [b"\x00\x00\xa0\xe1", b"\x04\x10\x9f\xe5"],  # ARM NOP, LDR
        "endian": "little",
    },
    "arm32-be": {
        "patterns": [b"\xe1\xa0\x00\x00", b"\xe5\x9f\x10\x04"],
        "endian": "big",
    },
    "mips-be": {
        "patterns": [b"\x00\x00\x00\x00", b"\x03\xe0\x00\x08"],  # NOP, JR $ra
        "endian": "big",
    },
    "mips-le": {
        "patterns": [b"\x08\x00\xe0\x03"],
        "endian": "little",
    },
    "x86": {
        "patterns": [b"\x55\x89\xe5", b"\x55\x8b\xec"],  # push ebp; mov ebp,esp
        "endian": "little",
    },
    "x86_64": {
        "patterns": [b"\x55\x48\x89\xe5", b"\xf3\x0f\x1e\xfa"],  # push rbp; endbr64
        "endian": "little",
    },
}

# Interesting string patterns
_SENSITIVE_PATTERNS = [
    (re.compile(rb"password[=: ]+\S+", re.IGNORECASE), "Possible credential"),
    (re.compile(rb"passwd[=: ]+\S+", re.IGNORECASE), "Possible credential"),
    (re.compile(rb"api[_-]?key[=: ]+\S+", re.IGNORECASE), "API key"),
    (re.compile(rb"secret[=: ]+\S+", re.IGNORECASE), "Secret value"),
    (re.compile(rb"BEGIN [A-Z]+ PRIVATE KEY"), "Embedded private key"),
    (re.compile(rb"-----BEGIN CERTIFICATE-----"), "Embedded certificate"),
    (re.compile(rb"http[s]?://[^\x00\s\"'<>]{8,100}"), "URL"),
    (re.compile(rb"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?"), "IP address"),
    (re.compile(rb"[A-Za-z0-9+/]{40,}={0,2}"), "Base64 blob (possible key)"),
    (re.compile(rb"/etc/[a-z/]+"), "Unix filesystem path"),
    (re.compile(rb"admin|root|guest|default", re.IGNORECASE), "Default account name"),
    (re.compile(rb"CVS|RCS|git|svn", re.IGNORECASE), "Version control artifact"),
    (re.compile(rb"debug|backdoor|test|TODO", re.IGNORECASE), "Debug/development artifact"),
]


class FirmwareAnalyzer:
    """
    Binary firmware analyzer.
    Entropy analysis, architecture detection, filesystem carving, string extraction.
    """

    def __init__(self, data_dir: str = "data/firmware", chunk_size: int = 256):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._chunk_size = chunk_size

    async def analyze(self, file_path: str) -> FirmwareReport:
        """
        Full firmware analysis.
        Returns: entropy map, architecture, filesystem signatures, sensitive strings.
        """
        p = Path(file_path)
        if not p.exists():
            return FirmwareReport(
                file_path=file_path, file_size=0, md5="", sha256="",
                architecture=ArchitectureHint("unknown", "unknown", 0.0, "File not found"),
                entropy_segments=[], filesystems=[], interesting_strings=[],
                security_findings=[], error=f"File not found: {file_path}",
            )

        file_data = p.read_bytes()
        return await asyncio.to_thread(self._analyze_sync, file_path, file_data)

    def _analyze_sync(self, file_path: str, data: bytes) -> FirmwareReport:
        import hashlib
        md5 = hashlib.md5(data).hexdigest()
        sha256 = hashlib.sha256(data).hexdigest()

        # Entropy analysis
        segments = self._compute_entropy_segments(data)

        # Architecture detection
        arch = self._detect_architecture(data)

        # Filesystem signatures
        filesystems = self._scan_filesystems(data)

        # String extraction
        strings, security_findings = self._extract_interesting_strings(data)

        # Entropy plot
        plot_path = self._plot_entropy(segments, file_path) if _MPL_OK else None

        return FirmwareReport(
            file_path=file_path,
            file_size=len(data),
            md5=md5,
            sha256=sha256,
            architecture=arch,
            entropy_segments=segments,
            filesystems=filesystems,
            interesting_strings=strings[:100],
            security_findings=security_findings,
            entropy_plot_path=plot_path,
        )

    def _compute_entropy_segments(self, data: bytes) -> List[EntropySegment]:
        segments = []
        for offset in range(0, len(data), self._chunk_size):
            chunk = data[offset:offset + self._chunk_size]
            if not chunk:
                break
            ent = self._entropy(chunk)

            if ent < 0.5:
                seg_type = "padding"
                desc = f"Zero-filled or padding region (entropy={ent:.2f})"
            elif ent < 3.0:
                seg_type = "data"
                desc = f"Low-entropy data (text/config/constants) (entropy={ent:.2f})"
            elif ent < 6.0:
                seg_type = "code"
                desc = f"Likely code/structured data (entropy={ent:.2f})"
            elif ent < 7.5:
                seg_type = "compressed"
                desc = f"High entropy — compressed data (entropy={ent:.2f})"
            else:
                seg_type = "encrypted"
                desc = f"Very high entropy — encrypted or random data (entropy={ent:.2f})"

            segments.append(EntropySegment(
                offset=offset,
                size=len(chunk),
                entropy=ent,
                segment_type=seg_type,
                description=desc,
            ))

        return segments

    def _detect_architecture(self, data: bytes) -> ArchitectureHint:
        best_arch = "unknown"
        best_conf = 0.0
        best_endian = "unknown"
        best_evidence = "No architecture patterns matched"

        for arch_name, info in _ARCH_PATTERNS.items():
            matches = sum(data.count(pat) for pat in info["patterns"])
            if matches > 0:
                conf = min(1.0, matches / 20)
                if conf > best_conf:
                    best_conf = conf
                    best_arch = arch_name.split("-")[0]
                    best_endian = info["endian"]
                    best_evidence = f"Matched {matches} instruction pattern(s) for {arch_name}"

        # ELF header detection
        if data[:4] == b"\x7fELF":
            ei_class = data[4] if len(data) > 4 else 0
            ei_data = data[5] if len(data) > 5 else 0
            e_machine = struct.unpack("<H", data[18:20])[0] if len(data) > 20 else 0
            arch_map = {
                3: "x86", 62: "x86_64", 40: "arm32",
                183: "arm64", 8: "mips", 243: "riscv",
            }
            best_arch = arch_map.get(e_machine, "unknown")
            best_endian = "little" if ei_data == 1 else "big"
            best_conf = 0.95
            best_evidence = f"ELF header: e_machine=0x{e_machine:04X} ({best_arch}), {'LE' if best_endian == 'little' else 'BE'}"

        return ArchitectureHint(
            arch=best_arch,
            endianness=best_endian,
            confidence=best_conf,
            evidence=best_evidence,
        )

    def _scan_filesystems(self, data: bytes) -> List[FilesystemSignature]:
        found = []
        for sig in _FS_SIGNATURES:
            magic = sig["magic"]
            search_offset = sig.get("offset", 0)
            
            # Search with alignment
            pos = 0
            while True:
                idx = data.find(magic, pos)
                if idx == -1:
                    break
                # For signatures with fixed internal offset (like ext2), verify
                if search_offset > 0:
                    check_pos = idx - search_offset
                    if check_pos >= 0:
                        found.append(FilesystemSignature(
                            offset=check_pos,
                            fs_type=sig["fs"],
                            description=sig["desc"],
                            magic_hex=magic.hex(),
                        ))
                else:
                    found.append(FilesystemSignature(
                        offset=idx,
                        fs_type=sig["fs"],
                        description=sig["desc"],
                        magic_hex=magic.hex(),
                    ))
                pos = idx + 1
                if len(found) > 50:
                    break

        return found

    def _extract_interesting_strings(self, data: bytes) -> Tuple[List[str], List[str]]:
        findings_set = []
        strings_set = set()

        # Printable string extraction (min 6 chars)
        printable = re.findall(rb"[ -~]{6,}", data)
        for s in printable[:500]:
            decoded = s.decode(errors="replace")
            strings_set.add(decoded)

        # Sensitive pattern search
        security_findings = []
        for pattern, label in _SENSITIVE_PATTERNS:
            matches = pattern.findall(data)
            for match in matches[:5]:
                decoded = match.decode(errors="replace")
                finding = f"[{label}] {decoded[:200]}"
                security_findings.append(finding)

        return sorted(strings_set)[:200], security_findings

    def _plot_entropy(self, segments: List[EntropySegment], file_path: str) -> str:
        offsets = [s.offset for s in segments]
        entropies = [s.entropy for s in segments]
        colors = []
        for s in segments:
            if s.segment_type == "encrypted":
                colors.append("#ff4444")
            elif s.segment_type == "compressed":
                colors.append("#ff9944")
            elif s.segment_type == "code":
                colors.append("#44aaff")
            elif s.segment_type == "padding":
                colors.append("#333333")
            else:
                colors.append("#44ff88")

        import os
        fname = os.path.basename(file_path)
        plot_path = str(self._data_dir / f"entropy_{fname}.png")

        fig, ax = plt.subplots(figsize=(14, 4))
        ax.bar(offsets, entropies, width=self._chunk_size * 0.9,
               color=colors, align="edge", linewidth=0)
        ax.axhline(y=7.0, color="#ff4444", linestyle="--", alpha=0.5, label="Encrypted threshold")
        ax.axhline(y=6.0, color="#ff9944", linestyle="--", alpha=0.5, label="Compressed threshold")
        ax.set_xlabel("File Offset (bytes)", color="#aaa")
        ax.set_ylabel("Entropy (bits/byte)", color="#aaa")
        ax.set_title(f"Firmware Entropy Map: {fname}", color="#00d4ff", fontsize=12)
        ax.set_ylim(0, 8.2)
        ax.tick_params(colors="#aaa")
        ax.set_facecolor("#0d0d0d")
        fig.patch.set_facecolor("#0d0d0d")
        ax.spines["bottom"].set_color("#333")
        ax.spines["left"].set_color("#333")
        ax.legend(facecolor="#1a1a2e", labelcolor="#aaa", fontsize=8)
        plt.tight_layout()
        plt.savefig(plot_path, dpi=120, bbox_inches="tight", facecolor="#0d0d0d")
        plt.close(fig)
        return plot_path

    def _entropy(self, data: bytes) -> float:
        if not data:
            return 0.0
        counter = collections.Counter(data)
        total = len(data)
        h = 0.0
        for count in counter.values():
            p = count / total
            h -= p * math.log2(p)
        return h
