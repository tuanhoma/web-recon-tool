"""Tests for core/deduplicator.py"""
import pytest
from models.endpoint import Endpoint
from core.deduplicator import Deduplicator


def _ep(path="/", params=None, risk_score=0, source_tools=None, tags=None, **kw) -> Endpoint:
    return Endpoint(
        url=f"https://example.com{path}",
        scheme="https",
        host="example.com",
        path=path,
        params=params or [],
        risk_score=risk_score,
        source_tools=source_tools or [],
        tags=tags or [],
        **kw,
    )


class TestDeduplicator:
    def setup_method(self):
        self.dedup = Deduplicator()

    def test_unique_endpoints_preserved(self):
        eps = [_ep("/a"), _ep("/b"), _ep("/c")]
        result = self.dedup.run(eps)
        assert len(result) == 3

    def test_duplicates_merged(self):
        ep1 = _ep("/search", params=["q"], risk_score=3, source_tools=["katana"])
        ep2 = _ep("/search", params=["q"], risk_score=1, source_tools=["httpx"])
        result = self.dedup.run([ep1, ep2])
        assert len(result) == 1

    def test_merge_keeps_higher_risk_score(self):
        ep_high = _ep("/api/users", params=["id"], risk_score=5, source_tools=["katana"])
        ep_low  = _ep("/api/users", params=["id"], risk_score=2, source_tools=["httpx"])
        result = self.dedup.run([ep_low, ep_high])
        assert result[0].risk_score == 5

    def test_merge_combines_source_tools(self):
        ep1 = _ep("/x", source_tools=["subfinder"])
        ep2 = _ep("/x", source_tools=["katana"])
        result = self.dedup.run([ep1, ep2])
        assert "subfinder" in result[0].source_tools
        assert "katana" in result[0].source_tools

    def test_merge_combines_tags(self):
        ep1 = _ep("/login", tags=["login"])
        ep2 = _ep("/login", tags=["dynamic"])
        result = self.dedup.run([ep1, ep2])
        assert "login" in result[0].tags
        assert "dynamic" in result[0].tags

    def test_different_paths_not_merged(self):
        ep1 = _ep("/user/1", params=["id"])
        ep2 = _ep("/post/1", params=["id"])
        result = self.dedup.run([ep1, ep2])
        assert len(result) == 2
