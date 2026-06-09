"""Scope — enforce target boundaries at every pipeline stage."""
from __future__ import annotations

import ipaddress
import re
from typing import List, Union


class ScopeChecker:
    """
    Validates whether a host/URL belongs to the authorised scope.

    Supports:
    - Exact domain match   e.g.  example.com
    - Wildcard subdomain   e.g.  *.example.com
    - CIDR range           e.g.  10.0.0.0/8
    - Extra allowed domains passed from config
    """

    def __init__(self, target: str, extra_domains: List[str] | None = None) -> None:
        self._target = target.lower().strip()
        self._extra: List[str] = [d.lower().strip() for d in (extra_domains or [])]
        self._networks: List[ipaddress.IPv4Network | ipaddress.IPv6Network] = []

        all_rules = [self._target] + self._extra
        cleaned: List[str] = []
        for rule in all_rules:
            try:
                self._networks.append(ipaddress.ip_network(rule, strict=False))
            except ValueError:
                cleaned.append(rule)
        self._domain_rules = cleaned

    # ------------------------------------------------------------------
    def is_in_scope(self, value: str) -> bool:
        """Return True if *value* (host or URL) is within scope."""
        host = self._extract_host(value)
        return self._check_host(host)

    def filter(self, values: List[str]) -> List[str]:
        """Return only the values that are in scope."""
        return [v for v in values if self.is_in_scope(v)]

    # ------------------------------------------------------------------
    def _extract_host(self, value: str) -> str:
        """Pull the hostname from a URL or return value as-is."""
        value = value.strip()
        if "://" in value:
            # strip scheme
            value = value.split("://", 1)[1]
        # strip path, port, query
        host = re.split(r"[:/\?#]", value)[0]
        return host.lower()

    def _check_host(self, host: str) -> bool:
        # IP address check
        try:
            addr = ipaddress.ip_address(host)
            return any(addr in net for net in self._networks)
        except ValueError:
            pass

        # Domain / wildcard check
        for rule in self._domain_rules:
            if rule.startswith("*."):
                # wildcard: *.example.com matches sub.example.com
                base = rule[2:]  # example.com
                if host == base or host.endswith("." + base):
                    return True
            else:
                if host == rule or host.endswith("." + rule):
                    return True
        return False
