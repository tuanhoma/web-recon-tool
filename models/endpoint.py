"""Endpoint — canonical data model flowing through the pipeline."""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class Endpoint(BaseModel):
    """Single discovered endpoint with all enrichment metadata."""

    # Core identity
    url: str
    scheme: str = ""
    host: str = ""
    path: str = "/"
    method: str = "GET"

    # Query parameters (keys only, sorted)
    params: List[str] = Field(default_factory=list)

    # Raw URL before normalisation
    raw_url: Optional[str] = None

    # httpx enrichment
    status: Optional[int] = None
    title: Optional[str] = None
    tech: List[str] = Field(default_factory=list)
    web_server: Optional[str] = None
    ip: Optional[str] = None
    is_cdn: bool = False

    # Pipeline metadata
    source_tools: List[str] = Field(default_factory=list)
    risk_score: int = 0
    tags: List[str] = Field(default_factory=list)
    is_interesting: bool = False
    discovered_at: datetime = Field(default_factory=datetime.utcnow)

    # Deduplication fingerprint (set by deduplicator)
    dedup_hash: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def _compute_hash(self) -> "Endpoint":
        """Auto-compute dedup_hash from scheme + host + path + sorted params."""
        if not self.dedup_hash:
            key = f"{self.scheme}://{self.host}{self.path}"
            if self.params:
                key += "?" + "&".join(sorted(self.params))
            self.dedup_hash = sha256(key.encode()).hexdigest()[:16]
        return self

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)

    def add_source(self, tool: str) -> None:
        if tool not in self.source_tools:
            self.source_tools.append(tool)


class ReconResult(BaseModel):
    """Top-level result object for a single recon run."""

    target: str
    subdomains: List[str] = Field(default_factory=list)
    alive_hosts: List[Dict[str, Any]] = Field(default_factory=list)
    endpoints: List[Endpoint] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
