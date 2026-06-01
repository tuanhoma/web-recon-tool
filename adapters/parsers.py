"""Parsers — convert raw tool output into Endpoint objects."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from models.endpoint import Endpoint
from utils.helpers import parse_url_partsth


# ---------------------------------------------------------------------------
# httpx JSON-lines parser
# ---------------------------------------------------------------------------

def parse_httpx_record(record: Dict[str, Any]) -> Optional[Endpoint]:
    """
    Parse a single httpx JSON record into an Endpoint.

    httpx JSON keys (subset):
      url, status_code, title, tech, webserver, ip, cdn, host
    """
    raw_url = record.get("url", "").strip()
    if not raw_url:
        return None

    parts = parse_url_parts(raw_url)

    tech_list: List[str] = []
    for t in record.get("tech", []) or []:
        if isinstance(t, str):
            tech_list.append(t)
        elif isinstance(t, dict):
            tech_list.append(t.get("name", str(t)))

    return Endpoint(
        url=raw_url,
        raw_url=raw_url,
        scheme=parts["scheme"],
        host=parts["host"],
        path=parts["path"],
        params=parts["params"],
        status=record.get("status_code"),
        title=record.get("title"),
        tech=tech_list,
        web_server=record.get("webserver"),
        ip=record.get("ip"),
        is_cdn=bool(record.get("cdn")),
        source_tools=["httpx"],
    )


def parse_httpx_results(records: List[Dict[str, Any]]) -> List[Endpoint]:
    endpoints: List[Endpoint] = []
    for rec in records:
        ep = parse_httpx_record(rec)
        if ep:
            endpoints.append(ep)
    return endpoints


# ---------------------------------------------------------------------------
# Katana line parser
# ---------------------------------------------------------------------------

def parse_katana_line(line: str) -> Optional[Endpoint]:
    """Parse a single URL line produced by katana into an Endpoint."""
    line = line.strip()
    if not line or not line.startswith(("http://", "https://")):
        return None

    parts = parse_url_parts(line)

    return Endpoint(
        url=line,
        raw_url=line,
        scheme=parts["scheme"],
        host=parts["host"],
        path=parts["path"],
        params=parts["params"],
        source_tools=["katana"],
        tags=["js_endpoint"] if ".js" in parts["path"] else [],
    )


def parse_katana_results(lines: List[str]) -> List[Endpoint]:
    endpoints: List[Endpoint] = []
    for line in lines:
        ep = parse_katana_line(line)
        if ep:
            endpoints.append(ep)
    return endpoints


# ---------------------------------------------------------------------------
# Feroxbuster JSON parser
# ---------------------------------------------------------------------------

def parse_ferox_record(record: Dict[str, Any]) -> Optional[Endpoint]:
    """Parse a feroxbuster JSON response record into an Endpoint."""
    raw_url = record.get("url", "").strip()
    if not raw_url:
        return None

    parts = parse_url_parts(raw_url)

    return Endpoint(
        url=raw_url,
        raw_url=raw_url,
        scheme=parts["scheme"],
        host=parts["host"],
        path=parts["path"],
        params=parts["params"],
        status=record.get("status"),
        source_tools=["feroxbuster"],
    )


def parse_
    ferox_results(records: List[Dict[str, Any]]) -> List[Endpoint]:
    endpoints: List[Endpoint] = []
    for rec in records:
        ep = parse_ferox_record(rec)
        if ep:
            endpoints.append(ep)
    return endpoints


# ---------------------------------------------------------------------------
# Arjun JSON parser
# ---------------------------------------------------------------------------

def parse_arjun_results(records: List[Dict[str, Any]]) -> List[Endpoint]:
    """
    Arjun output format:
      [{"url": "...", "params": {"param1": "value", ...}}, ...]
    """
    endpoints: List[Endpoint] = []
    for rec in records:
        raw_url = rec.get("url", "").strip()
        if not raw_url:
            continue
        parts = parse_url_parts(raw_url)
        discovered_params = list((rec.get("params") or {}).keys())
        merged_params = sorted(set(parts["params"] + discovered_params))

        ep = Endpoint(
            url=raw_url,
            raw_url=raw_url,
            scheme=parts["scheme"],
            host=parts["host"],
            path=parts["path"],
            params=merged_params,
            source_tools=["arjun"],
        )
        endpoints.append(ep)
    return endpoints
