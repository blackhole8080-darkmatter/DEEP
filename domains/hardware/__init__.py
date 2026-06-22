"""
DEEP — Hardware Domain
Firmware analysis, entropy scanner, string extraction, architecture detection.
"""
from .firmware_analyzer import FirmwareAnalyzer, FirmwareReport, EntropySegment
from .string_extractor import StringExtractor, ExtractedString

__all__ = [
    "FirmwareAnalyzer", "FirmwareReport", "EntropySegment",
    "StringExtractor", "ExtractedString",
]
