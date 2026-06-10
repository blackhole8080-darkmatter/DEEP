# deep/security_ops.py — Local Security, Defensive (Bible Section 26.5)
"""Connect-scan (own host), file-hash verify, secure password gen, AES file
encrypt/decrypt, network-connection listing, HIBP k-anonymity check. Defensive
only. cryptography/argon2/psutil optional."""
from __future__ import annotations

import hashlib
import math
import os
import re
import secrets
import socket
import string
from concurrent.futures import ThreadPoolExecutor

try:
    import psutil
    PSUTIL = True
except Exception:  # pragma: no cover
    PSUTIL = False

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    CRYPTO = True
except Exception:  # pragma: no cover
    CRYPTO = False

COMMON_SERVICES = {22: "ssh", 80: "http", 443: "https", 3306: "mysql",
                   5432: "postgres", 6379: "redis", 7768: "deep", 8000: "http-alt",
                   11434: "ollama", 27017: "mongodb"}


class SecurityOps:
    def __init__(self, config=None):
        self.config = config

    def scan_open_ports(self, host="127.0.0.1", port_range=(1, 1024), timeout=0.2) -> dict:
        if host not in ("127.0.0.1", "localhost", "::1"):
            # still allow, but warn
            warn = f" (warning: {host} is not localhost)"
        else:
            warn = ""
        ports = list(range(port_range[0], port_range[1] + 1))

        def probe(p):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            try:
                return p if s.connect_ex((host, p)) == 0 else None
            finally:
                s.close()
        with ThreadPoolExecutor(max_workers=200) as ex:
            open_ports = [p for p in ex.map(probe, ports) if p]
        results = [{"port": p, "service": COMMON_SERVICES.get(p, "unknown")}
                   for p in open_ports]
        return {"open_ports": results, "result": open_ports,
                "verbal": f"Scan of {host}{warn}: open ports " +
                          (", ".join(f"{r['port']}({r['service']})" for r in results)
                           if results else "none") + ", sir."}

    def check_file_hash(self, path, expected, algorithm="sha256") -> dict:
        h = hashlib.new(algorithm)
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        computed = h.hexdigest()
        return {"computed": computed, "match": computed == expected,
                "result": computed == expected,
                "verbal": f"Hash {'matches' if computed == expected else 'does NOT match'}, sir."}

    def generate_password(self, length=20, complexity="high") -> dict:
        sets = {"low": string.ascii_letters,
                "medium": string.ascii_letters + string.digits,
                "high": string.ascii_letters + string.digits + "!@#$%^&*()-_=+"}
        alpha = sets.get(complexity, sets["high"])
        pw = "".join(secrets.choice(alpha) for _ in range(length))
        entropy = length * math.log2(len(alpha))
        return {"password": pw, "entropy_bits": round(entropy, 1), "result": pw,
                "verbal": f"Generated a {length}-char password ({entropy:.0f} bits), sir: {pw}"}

    def encrypt_file(self, path, password, output=None) -> dict:
        if not CRYPTO:
            return {"result": None, "verbal": "cryptography not installed, sir."}
        key = hashlib.sha256(password.encode()).digest()
        nonce = os.urandom(12)
        data = open(path, "rb").read()
        ct = AESGCM(key).encrypt(nonce, data, None)
        output = output or path + ".enc"
        open(output, "wb").write(nonce + ct)
        return {"encrypted_path": output, "result": output,
                "verbal": f"Encrypted to {os.path.basename(output)} (AES-256-GCM), sir."}

    def decrypt_file(self, path, password, output=None) -> dict:
        if not CRYPTO:
            return {"result": None, "verbal": "cryptography not installed, sir."}
        key = hashlib.sha256(password.encode()).digest()
        blob = open(path, "rb").read()
        pt = AESGCM(key).decrypt(blob[:12], blob[12:], None)
        output = output or path.replace(".enc", ".dec")
        open(output, "wb").write(pt)
        return {"decrypted_path": output, "result": output,
                "verbal": f"Decrypted to {os.path.basename(output)}, sir."}

    def list_network_connections(self) -> dict:
        if not PSUTIL:
            return {"result": None, "verbal": "psutil not installed, sir."}
        conns = []
        for c in psutil.net_connections(kind="inet"):
            if c.raddr:
                conns.append({"local": f"{c.laddr.ip}:{c.laddr.port}",
                              "remote": f"{c.raddr.ip}:{c.raddr.port}",
                              "status": c.status, "pid": c.pid})
        return {"connections": conns, "result": len(conns),
                "verbal": f"{len(conns)} active remote connection(s), sir."}

    def check_password_breached(self, password) -> dict:
        sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]
        try:
            import requests
            r = requests.get(f"https://api.pwnedpasswords.com/range/{prefix}", timeout=5)
            count = 0
            for line in r.text.splitlines():
                h, c = line.split(":")
                if h == suffix:
                    count = int(c); break
            return {"breached": count > 0, "count": count, "result": count,
                    "verbal": (f"That password appears in {count} breaches, sir — change it!"
                               if count else "That password was not found in breaches, sir.")}
        except Exception as e:  # noqa: BLE001
            return {"result": None, "verbal": f"HIBP check needs network, sir: {e}"}

    def test(self) -> None:
        s = self.scan_open_ports("127.0.0.1", (7760, 7770))
        assert "open_ports" in s
        pw = self.generate_password(16)
        assert len(pw["password"]) == 16
        print("security_ops.SecurityOps: OK")


_engine = SecurityOps()


def scan(text: str) -> dict:
    low = text.lower()
    if "connection" in low:
        return _engine.list_network_connections()
    m = re.search(r"\b(\d+\.\d+\.\d+\.\d+|localhost)\b", text)
    host = m.group(1) if m else "127.0.0.1"
    return _engine.scan_open_ports(host, (1, 1024))


def test() -> None:
    SecurityOps().test()


if __name__ == "__main__":
    test()
