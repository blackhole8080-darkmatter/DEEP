"""
DEEP — Binary Protocol Reverse Engineer
Entropy analysis, field boundary detection, magic byte identification.
"""
from __future__ import annotations

import collections
import math
import struct
from dataclasses import dataclass, field
from typing import List


@dataclass
class ProtocolField:
    offset: int
    size: int               # bytes
    field_type: str         # "magic" | "length" | "sequence" | "command" | "checksum" | "payload" | "unknown"
    example_values: List[str]   # hex strings
    description: str
    entropy: float = 0.0
    is_constant: bool = False


@dataclass
class InferredProtocol:
    name: str
    description: str
    fields: List[ProtocolField]
    header_size: int
    entropy_bits_per_byte: float
    is_encrypted: bool
    has_magic: bool
    has_length_field: bool
    has_sequence: bool
    has_checksum: bool
    security_issues: List[str] = field(default_factory=list)
    confidence: float = 0.0


class BinaryProtocolRE:
    """
    Reverse engineer an unknown binary protocol from sample payloads.
    Input: list of raw bytes samples (minimum 10 recommended)
    """

    def analyze(self, samples: List[bytes]) -> InferredProtocol:
        """
        Analyze binary protocol samples.
        Returns structured InferredProtocol with field boundaries and types.
        """
        if not samples:
            return InferredProtocol(
                name="Unknown",
                description="No samples provided",
                fields=[],
                header_size=0,
                entropy_bits_per_byte=0.0,
                is_encrypted=False,
                has_magic=False,
                has_length_field=False,
                has_sequence=False,
                has_checksum=False,
            )

        # Normalize: trim all samples to the minimum length
        min_len = min(len(s) for s in samples)
        samples_trimmed = [s[:min_len] for s in samples if len(s) >= 4]

        if not samples_trimmed:
            return InferredProtocol(
                name="Unknown", description="Samples too short",
                fields=[], header_size=0, entropy_bits_per_byte=0.0,
                is_encrypted=False, has_magic=False, has_length_field=False,
                has_sequence=False, has_checksum=False,
            )

        # Global entropy
        all_bytes = b"".join(samples)
        global_entropy = self._entropy(all_bytes)

        # Per-position entropy and value distribution
        per_pos_entropy = [
            self._entropy(bytes(s[i] for s in samples_trimmed))
            for i in range(min_len)
        ]
        per_pos_values = [
            list(set(s[i] for s in samples_trimmed))
            for i in range(min_len)
        ]

        # Field detection
        fields = []

        # Step 1: Magic bytes (first 2-4 bytes, very low entropy, constant)
        has_magic = False
        if min_len >= 2:
            magic_end = 0
            for i in range(min(4, min_len)):
                if per_pos_entropy[i] < 0.3 and len(per_pos_values[i]) == 1:
                    magic_end = i + 1
            if magic_end >= 1:
                has_magic = True
                magic_bytes = [f"0x{samples_trimmed[0][j]:02X}" for j in range(magic_end)]
                fields.append(ProtocolField(
                    offset=0, size=magic_end,
                    field_type="magic",
                    example_values=[" ".join(magic_bytes)],
                    description=f"Magic header: {' '.join(magic_bytes)} (constant across all samples)",
                    entropy=sum(per_pos_entropy[:magic_end]) / magic_end,
                    is_constant=True,
                ))

        # Step 2: Command byte (low-medium entropy, small value range, after magic)
        start_after_magic = sum(1 for f in fields if f.field_type == "magic")
        has_command = False
        for i in range(start_after_magic, min(start_after_magic + 2, min_len)):
            vals = per_pos_values[i]
            if 1 < len(vals) <= 16 and per_pos_entropy[i] < 2.5:
                has_command = True
                fields.append(ProtocolField(
                    offset=i, size=1,
                    field_type="command",
                    example_values=[f"0x{v:02X}" for v in sorted(vals)[:8]],
                    description=f"Command/type byte ({len(vals)} distinct values)",
                    entropy=per_pos_entropy[i],
                ))
                break

        # Step 3: Sequence number (monotonically increasing across samples)
        has_sequence = False
        for size in (2, 4, 1):
            for i in range(start_after_magic, min_len - size + 1):
                values = []
                for s in samples_trimmed:
                    if size == 1:
                        values.append(s[i])
                    elif size == 2:
                        values.append(struct.unpack(">H", s[i:i+2])[0])
                    else:
                        values.append(struct.unpack(">I", s[i:i+4])[0])
                if self._is_sequential(values):
                    has_sequence = True
                    fields.append(ProtocolField(
                        offset=i, size=size,
                        field_type="sequence",
                        example_values=[str(v) for v in values[:5]],
                        description=f"Sequence number (uint{size*8}-be, incrementing)",
                        entropy=per_pos_entropy[i],
                    ))
                    break
            if has_sequence:
                break

        # Step 4: Length field (correlates with sample length variation)
        has_length_field = False
        if len(samples) > 1:
            lengths = [len(s) for s in samples]
            for size in (2, 4, 1):
                for i in range(start_after_magic, min_len - size + 1):
                    field_vals = []
                    for s in samples_trimmed:
                        if size == 1:
                            field_vals.append(s[i])
                        elif size == 2:
                            field_vals.append(struct.unpack(">H", s[i:i+2])[0])
                        else:
                            field_vals.append(struct.unpack(">I", s[i:i+4])[0])
                    # Check correlation with payload length
                    corr = self._length_correlation(field_vals, [s - (i + size) for s in [len(x) for x in samples_trimmed]])
                    if corr > 0.8:
                        has_length_field = True
                        fields.append(ProtocolField(
                            offset=i, size=size,
                            field_type="length",
                            example_values=[str(v) for v in field_vals[:5]],
                            description=f"Payload length field (uint{size*8}-be, correlation={corr:.2f})",
                            entropy=per_pos_entropy[i],
                        ))
                        break
                if has_length_field:
                    break

        # Step 5: Checksum (last 1-4 bytes, high entropy)
        has_checksum = False
        if min_len >= 4:
            tail_entropy = per_pos_entropy[-2:]
            if all(e > 3.0 for e in tail_entropy):
                has_checksum = True
                tail_bytes = [f"0x{samples_trimmed[0][j]:02X}" for j in range(min_len-2, min_len)]
                fields.append(ProtocolField(
                    offset=min_len - 2, size=2,
                    field_type="checksum",
                    example_values=[" ".join(tail_bytes)],
                    description="Possible 2-byte checksum/CRC (high entropy at end of packet)",
                    entropy=sum(tail_entropy) / 2,
                ))

        # Sort fields by offset
        fields.sort(key=lambda f: f.offset)

        # Security issues
        security_issues = []
        if not has_sequence:
            security_issues.append("No sequence number detected — replay attacks may be possible")
        if not has_checksum:
            security_issues.append("No checksum/integrity field detected — packet tampering undetected")
        if global_entropy < 2.0 and not has_magic:
            security_issues.append("Very low entropy — protocol appears plaintext/unencrypted")
        if global_entropy > 6.5:
            security_issues.append("High entropy suggests encryption or compression — protocol may be TLS-wrapped")

        return InferredProtocol(
            name="Inferred Protocol",
            description=f"Analyzed from {len(samples)} samples, {min_len} bytes each",
            fields=fields,
            header_size=sum(f.size for f in fields if f.field_type != "payload"),
            entropy_bits_per_byte=global_entropy,
            is_encrypted=global_entropy > 7.0,
            has_magic=has_magic,
            has_length_field=has_length_field,
            has_sequence=has_sequence,
            has_checksum=has_checksum,
            security_issues=security_issues,
            confidence=self._estimate_confidence(fields, len(samples)),
        )

    def _entropy(self, data: bytes) -> float:
        if not data:
            return 0.0
        counter = collections.Counter(data)
        total = len(data)
        entropy = 0.0
        for count in counter.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy

    def _is_sequential(self, values: List[int]) -> bool:
        if len(values) < 3:
            return False
        diffs = [values[i+1] - values[i] for i in range(len(values)-1)]
        return len(set(diffs)) == 1 and diffs[0] > 0

    def _length_correlation(self, field_vals: List[int], payload_lens: List[int]) -> float:
        if len(field_vals) < 3:
            return 0.0
        try:
            n = len(field_vals)
            mean_f = sum(field_vals) / n
            mean_p = sum(payload_lens) / n
            num = sum((f - mean_f) * (p - mean_p) for f, p in zip(field_vals, payload_lens))
            den_f = math.sqrt(sum((f - mean_f) ** 2 for f in field_vals))
            den_p = math.sqrt(sum((p - mean_p) ** 2 for p in payload_lens))
            if den_f == 0 or den_p == 0:
                return 0.0
            return abs(num / (den_f * den_p))
        except Exception:
            return 0.0

    def _estimate_confidence(self, fields: List[ProtocolField], n_samples: int) -> float:
        score = 0.0
        score += min(0.3, n_samples / 100)  # more samples = more confident
        score += 0.15 * any(f.field_type == "magic" for f in fields)
        score += 0.15 * any(f.field_type == "command" for f in fields)
        score += 0.15 * any(f.field_type == "length" for f in fields)
        score += 0.15 * any(f.field_type == "sequence" for f in fields)
        score += 0.1 * any(f.field_type == "checksum" for f in fields)
        return round(min(1.0, score), 2)
