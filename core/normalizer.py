"""Normalizer — clean and standardise Endpoint URLs before deduplication."""
from __future__ import annotations

from typing import List

from models.endpoint import Endpoint
from utils.helpers import normalize_path, parse_url_parts

# Tracking params already stripped in parse_url_parts; these are extra noise
_EXTRA_NOISE_PARAMS = frozenset(
    {"sessionid", "csrftoken", "nonce", "_csrf", "__cf_chl_jschl_tk__"}
)


class Normalizer:
    """
    Applies URL normalisation rules to a list of Endpoint objects:

    1. Re-compute scheme/host/path/params from raw_url (in case they differ)
    2. Normalise dynamic path segments  /user/123 → /user/{id}
    3. Strip additional noise params beyond the tracking list
    4. Rebuild the canonical ``url`` field
    """

    def run(self, endpoints: List[Endpoint]) -> List[Endpoint]:
        normalised: List[Endpoint] = []
        for ep in endpoints:
            normalised.append(self._normalize(ep))
        return normalised

    # ------------------------------------------------------------------

    def _normalize(self, ep: Endpoint) -> Endpoint:
        source = ep.raw_url or ep.url
        parts = parse_url_parts(source)

        # Normalise path (replace id segments)
        norm_path = normalize_path(parts["path"])

        # Strip extra noise params
        clean_params = [
            p for p in parts["params"]
            if p not in _EXTRA_NOISE_PARAMS
        ]

        # Rebuild canonical URL
        canon_url = f"{parts['scheme']}://{parts['host']}{norm_path}"
        if clean_params:
            canon_url += "?" + "&".join(f"{p}=" for p in clean_params)

        # Return a new Endpoint with updated fields (Pydantic model_copy)
        return ep.model_copy(update={
            "url": canon_url,
            "scheme": parts["scheme"],
            "host": parts["host"],
            "path": norm_path,
            "params": clean_params,
            "dedup_hash": None,  # force recompute in validator
        })
