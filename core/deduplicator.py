"""Deduplicator — merge duplicate Endpoints by hash, keeping best metadata."""
from __future__ import annotations

from typing import Dict, List

from models.endpoint import Endpoint


class Deduplicator:
    """
    Deduplicates a list of Endpoints using ``dedup_hash``.

    Merge strategy (when two endpoints share the same hash):
    - Keep the one with the **higher risk_score**
    - Merge ``source_tools``, ``tech``, and ``tags`` from both
    - Merge ``params`` (union)
    - Prefer non-None values for ``status``, ``title``, ``ip``, ``web_server``
    """

    def run(self, endpoints: List[Endpoint]) -> List[Endpoint]:
        seen: Dict[str, Endpoint] = {}

        for ep in endpoints:
            key = ep.dedup_hash or ep.url
            if key not in seen:
                seen[key] = ep
            else:
                seen[key] = self._merge(seen[key], ep)

        return list(seen.values())

    # ------------------------------------------------------------------

    def _merge(self, existing: Endpoint, incoming: Endpoint) -> Endpoint:
        """Return a merged Endpoint, favouring the higher-scoring one."""
        base, other = (
            (existing, incoming)
            if existing.risk_score >= incoming.risk_score
            else (incoming, existing)
        )

        # Merge list fields
        merged_sources = list(dict.fromkeys(base.source_tools + other.source_tools))
        merged_tech    = list(dict.fromkeys(base.tech + other.tech))
        merged_tags    = list(dict.fromkeys(base.tags + other.tags))
        merged_params  = sorted(set(base.params + other.params))

        return base.model_copy(update={
            "source_tools": merged_sources,
            "tech":         merged_tech,
            "tags":         merged_tags,
            "params":       merged_params,
            "status":       base.status or other.status,
            "title":        base.title or other.title,
            "ip":           base.ip or other.ip,
            "web_server":   base.web_server or other.web_server,
            "is_cdn":       base.is_cdn or other.is_cdn,
        })
