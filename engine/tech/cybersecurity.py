# deep/tech/cybersecurity.py — Cybersecurity, Defensive (Bible Section 21)
"""STRICTLY DEFENSIVE: hashing, symmetric/asymmetric crypto, password-strength
analysis, file entropy/static analysis, connect-scan of your own host. No
offensive exploit code. `cryptography` is optional and guarded."""
from __future__ import annotations

import hashlib
import math
import os
import re
import secrets
import socket
import string
from collections import Counter

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives import hashes, serialization
    CRYPTO = True
except Exception:  # pragma: no cover
    CRYPTO = False

COMMON_PASSWORDS = {"password", "123456", "qwerty", "admin", "letmein", "welcome",
                    "monkey", "111111", "iloveyou", "abc123", "password1"}


class SecurityEngine:
    def __init__(self, config=None):
        self.config = config

    # ── hashing ─────────────────────────────────────────────────────
    def hash_data(self, data, algorithm="sha256") -> dict:
        if isinstance(data, str):
            data = data.encode()
        algos = {"md5": hashlib.md5, "sha1": hashlib.sha1, "sha256": hashlib.sha256,
                 "sha512": hashlib.sha512}
        h = algos.get(algorithm, hashlib.sha256)(data).hexdigest()
        return {"algorithm": algorithm, "digest": h, "result": h,
                "verbal": f"{algorithm.upper()} digest: {h[:32]}…"}

    # ── symmetric crypto ────────────────────────────────────────────
    def aes_encrypt(self, plaintext, key=None) -> dict:
        if not CRYPTO:
            return {"result": None, "verbal": "AES needs the cryptography library, sir."}
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()
        key = key or AESGCM.generate_key(bit_length=256)
        nonce = os.urandom(12)
        ct = AESGCM(key).encrypt(nonce, plaintext, None)
        return {"ciphertext": ct.hex(), "nonce": nonce.hex(), "key": key.hex(),
                "result": ct.hex(),
                "verbal": f"AES-256-GCM encrypted {len(plaintext)} bytes "
                          f"(ciphertext {len(ct)} bytes)."}

    def aes_decrypt(self, ciphertext_hex, key_hex, nonce_hex) -> dict:
        if not CRYPTO:
            return {"result": None, "verbal": "AES needs the cryptography library, sir."}
        pt = AESGCM(bytes.fromhex(key_hex)).decrypt(
            bytes.fromhex(nonce_hex), bytes.fromhex(ciphertext_hex), None)
        return {"plaintext": pt.decode(errors="replace"), "result": pt.decode(errors="replace"),
                "verbal": f"Decrypted: {pt.decode(errors='replace')[:60]}"}

    def rsa_demo(self, message="DEEP secure") -> dict:
        if not CRYPTO:
            return {"result": None, "verbal": "RSA needs the cryptography library, sir."}
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        sig = key.sign(message.encode(),
                       padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                   salt_length=padding.PSS.MAX_LENGTH),
                       hashes.SHA256())
        try:
            key.public_key().verify(
                sig, message.encode(),
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                            salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256())
            verified = True
        except Exception:
            verified = False
        return {"signature_len": len(sig), "verified": verified, "result": verified,
                "verbal": f"RSA-2048 sign/verify of '{message}': "
                          f"signature {'valid' if verified else 'invalid'}."}

    # ── password analysis ───────────────────────────────────────────
    def password_analysis(self, password) -> dict:
        pool = 0
        if any(c.islower() for c in password): pool += 26
        if any(c.isupper() for c in password): pool += 26
        if any(c.isdigit() for c in password): pool += 10
        if any(c in string.punctuation for c in password): pool += len(string.punctuation)
        entropy = len(password) * math.log2(pool) if pool else 0
        # crack time at 1e10 guesses/sec
        guesses = 0.5 * (pool ** len(password)) if pool else 0
        seconds = guesses / 1e10
        common = password.lower() in COMMON_PASSWORDS
        if common:
            strength = "very weak (common password)"
        elif entropy < 28:
            strength = "very weak"
        elif entropy < 36:
            strength = "weak"
        elif entropy < 60:
            strength = "reasonable"
        elif entropy < 128:
            strength = "strong"
        else:
            strength = "very strong"
        return {"entropy_bits": round(entropy, 1), "strength": strength,
                "crack_time_seconds": seconds, "common": common,
                "result": {"entropy_bits": round(entropy, 1), "strength": strength},
                "verbal": f"Password strength: {strength} ({entropy:.0f} bits of entropy, "
                          f"~{_human_time(seconds)} to brute-force)."}

    def generate_password(self, length=16) -> dict:
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        return {"password": pw, "result": pw,
                "verbal": f"Generated a {length}-character password: {pw}"}

    # ── file static analysis ────────────────────────────────────────
    def file_entropy(self, data) -> dict:
        if isinstance(data, str):
            data = data.encode()
        if not data:
            return {"entropy": 0.0, "result": 0.0, "verbal": "Empty data, sir."}
        counts = Counter(data)
        n = len(data)
        ent = -sum((c / n) * math.log2(c / n) for c in counts.values())
        packed = ent > 7.5
        return {"entropy": round(ent, 4), "likely_packed_or_encrypted": packed,
                "result": {"entropy": round(ent, 4)},
                "verbal": f"Byte entropy {ent:.3f}/8.0 — "
                          f"{'likely packed/encrypted' if packed else 'normal'}."}

    # ── connect scan (own host) ─────────────────────────────────────
    def port_scan(self, target="127.0.0.1", ports=(22, 80, 443, 8000, 7768), timeout=0.3) -> dict:
        open_ports = []
        for p in ports:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            try:
                if s.connect_ex((target, p)) == 0:
                    open_ports.append(p)
            except Exception:
                pass
            finally:
                s.close()
        return {"target": target, "open_ports": open_ports, "result": open_ports,
                "verbal": f"Connect-scan of {target}: open ports {open_ports or 'none'}."}

    def test(self) -> None:
        assert self.hash_data("abc")["digest"] == hashlib.sha256(b"abc").hexdigest()
        weak = self.password_analysis("123456")
        assert weak["common"]
        strong = self.password_analysis("Tr0ub4dor&3xKplrZ!")
        assert strong["entropy_bits"] > weak["entropy_bits"]
        assert self.file_entropy(os.urandom(1000))["likely_packed_or_encrypted"]
        print("cybersecurity.SecurityEngine: OK")


def _human_time(seconds):
    if seconds < 1:
        return "under a second"
    for unit, s in (("years", 3.156e7), ("days", 86400), ("hours", 3600),
                    ("minutes", 60)):
        if seconds >= s:
            return f"{seconds/s:.1f} {unit}"
    return f"{seconds:.0f} seconds"


_engine = SecurityEngine()


def analyze(text: str) -> dict:
    low = text.lower()
    m = re.search(r"password\s+(?:is\s+|of\s+)?[\"']?(\S+)[\"']?", text, re.I)
    if "password" in low and m:
        return _engine.password_analysis(m.group(1))
    if "port" in low or "scan" in low:
        return _engine.port_scan()
    if "entropy" in low:
        return _engine.file_entropy(os.urandom(512))
    return {"result": None,
            "verbal": "I run defensive analysis only, sir: password strength, file "
                      "entropy, hashing, crypto, and connect-scans of your own host."}


def crypto(text: str) -> dict:
    low = text.lower()
    payload = re.sub(r"^.*?(hash|encrypt|decrypt|sign|cipher|rsa|aes)\b[:,]?\s*",
                     "", text, flags=re.I).strip()
    if "hash" in low:
        algo = next((a for a in ("sha512", "sha256", "sha1", "md5") if a in low), "sha256")
        return _engine.hash_data(payload or "DEEP", algo)
    if "rsa" in low or "sign" in low:
        return _engine.rsa_demo(payload or "DEEP secure")
    if "encrypt" in low or "aes" in low:
        return _engine.aes_encrypt(payload or "DEEP secret")
    if "generate" in low and "password" in low:
        return _engine.generate_password()
    return _engine.hash_data(payload or "DEEP", "sha256")


def test() -> None:
    SecurityEngine().test()


if __name__ == "__main__":
    test()
