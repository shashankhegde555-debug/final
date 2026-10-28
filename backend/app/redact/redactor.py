import re
import hashlib
from typing import Dict, Any, Union

class RedactionEngine:
    def __init__(self):
        # Match IP address without port in capture group 1, and optional port in capture group 2
        self._ip_regex = re.compile(
            r'\b((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))(?::(\d+))?\b'
        )
        self._ipv6_regex = re.compile(
            r'\b((?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4})\b'
        )
        self._host_regex = re.compile(
            r'\b((?:[a-zA-Z0-9-]+\.)+(?:internal|corp|local|ec2|compute|aws|lan|com|net|org))(?::(\d+))?\b'
        )
        self._customer_regex = re.compile(
            r'\b((?:cust|tenant|user|org|client)[-_]?[a-zA-Z0-9]{4,16})\b',
            re.IGNORECASE
        )
        self._ip_cache: Dict[str, str] = {}
        self._host_cache: Dict[str, str] = {}
        self._cust_cache: Dict[str, str] = {}

    def _pseudonymize(self, val: str, prefix: str, cache: Dict[str, str]) -> str:
        clean = val.lower().strip()
        if clean not in cache:
            h = hashlib.sha256(clean.encode()).hexdigest()[:6]
            cache[clean] = f"{prefix}-{h}"
        return cache[clean]

    def redact_text(self, text: str, enabled: bool = True) -> str:
        if not text or not enabled:
            return text

        # Redact IPv4 (preserving optional port suffix)
        def replace_ip(match):
            ip_val = match.group(1)
            port_val = match.group(2)
            pseudo = self._pseudonymize(ip_val, "ip", self._ip_cache)
            return f"{pseudo}:{port_val}" if port_val else pseudo

        text = self._ip_regex.sub(replace_ip, text)

        # Redact IPv6
        def replace_ipv6(match):
            raw = match.group(1)
            return self._pseudonymize(raw, "ip6", self._ip_cache)
        text = self._ipv6_regex.sub(replace_ipv6, text)

        # Redact Hostnames
        def replace_host(match):
            host_val = match.group(1)
            port_val = match.group(2)
            pseudo = self._pseudonymize(host_val, "host", self._host_cache)
            return f"{pseudo}:{port_val}" if port_val else pseudo

        text = self._host_regex.sub(replace_host, text)

        # Redact Customer / Tenant IDs
        def replace_cust(match):
            raw = match.group(1)
            return self._pseudonymize(raw, "cust", self._cust_cache)
        text = self._customer_regex.sub(replace_cust, text)

        return text

    def redact_alert_dict(self, d: Dict[str, Any], enabled: bool = True) -> Dict[str, Any]:
        if not enabled:
            return d
        out = dict(d)
        if "message" in out and isinstance(out["message"], str):
            out["message"] = self.redact_text(out["message"], enabled)
        if "host" in out and isinstance(out["host"], str) and out["host"]:
            out["host"] = self._pseudonymize(out["host"], "host", self._host_cache)
        if "customer_ref" in out and isinstance(out["customer_ref"], str) and out["customer_ref"]:
            out["customer_ref"] = self._pseudonymize(out["customer_ref"], "cust", self._cust_cache)
        return out

redactor = RedactionEngine()
