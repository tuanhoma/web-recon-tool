"""Helpers — URL parsing and misc utilities used across the pipeline."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse


# Tracking / noise params to strip before dedup
_TRACKING_PARAMS = frozenset(
    {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "fbclid", "gclid", "msclkid", "_ga", "_gl", "ref", "_t", "yclid",
        "mc_eid", "mc_cid",
    }
)

# Path segments that look like IDs
_ID_PATTERN = re.compile(
    r"^(\d+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{24,32})$",
    re.IGNORECASE,
)


def parse_url_parts(url: str) -> Dict[str, object]:
    """
    Parse a URL into its constituent parts.

    Returns a dict with keys:
      scheme, host, path, params (List[str] — keys only, no tracking, sorted)
    """
    parsed = urlparse(url.strip())
    scheme = parsed.scheme or "https"
    host = parsed.netloc.lower()
    path = parsed.path or "/"

    qs = parse_qs(parsed.query, keep_blank_values=False)
    params: List[str] = sorted(
        k for k in qs.keys() if k not in _TRACKING_PARAMS
    )

    return {"scheme": scheme, "host": host, "path": path, "params": params}


def is_dynamic_path(path: str) -> bool:
    """Return True if the path contains numeric/UUID segments (dynamic routes)."""
    segments = path.strip("/").split("/")
    return any(_ID_PATTERN.match(seg) for seg in segments if seg)


def normalize_path(path: str) -> str:
    """
    Replace dynamic path segments with ``{id}`` placeholder.

    /user/12345/profile  →  /user/{id}/profile
    """
    segments = path.strip("/").split("/")
    normalized = ["{id}" if _ID_PATTERN.match(seg) and seg else seg for seg in segments]
    return "/" + "/".join(normalized)


def sanitize_filename(name: str) -> str:
    """Make a string safe for use as a filename/directory name."""
    return re.sub(r"[^\w\-.]", "_", name)


def ensure_output_dir(base: str, target: str) -> Path:
    """Create and return the output directory for a given target."""
    out = Path(base) / sanitize_filename(target)
    out.mkdir(parents=True, exist_ok=True)
    return out
