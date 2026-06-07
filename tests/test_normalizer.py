"""Tests for core/normalizer.py"""
import pytest
from models.endpoint import Endpoint
from core.normalizer import Normalizer


def _ep(**kwargs) -> Endpoint:
    defaults = dict(url="https://example.com/", scheme="https", host="example.com", path="/")
    defaults.update(kwargs)
    return Endpoint(**defaults)


class TestNormalizer:
    def setup_method(self):
        self.norm = Normalizer()

    def test_dynamic_id_replaced(self):
        ep = _ep(url="https://example.com/user/12345", raw_url="https://example.com/user/12345",
                 path="/user/12345")
        result = self.norm.run([ep])
        assert result[0].path == "/user/{id}"

    def test_uuid_replaced(self):
        uuid = "550e8400-e29b-41d4-a716-446655440000"
        ep = _ep(url=f"https://example.com/order/{uuid}",
                 raw_url=f"https://example.com/order/{uuid}",
                 path=f"/order/{uuid}")
        result = self.norm.run([ep])
        assert result[0].path == "/order/{id}"

    def test_static_path_unchanged(self):
        ep = _ep(url="https://example.com/about", raw_url="https://example.com/about",
                 path="/about")
        result = self.norm.run([ep])
        assert result[0].path == "/about"

    def test_tracking_params_stripped(self):
        raw = "https://example.com/page?utm_source=google&q=test"
        ep = _ep(url=raw, raw_url=raw, path="/page", params=["utm_source", "q"])
        result = self.norm.run([ep])
        assert "utm_source" not in result[0].params
        assert "q" in result[0].params

    def test_returns_same_count(self):
        eps = [
            _ep(url=f"https://example.com/path/{i}", raw_url=f"https://example.com/path/{i}",
                path=f"/path/{i}")
            for i in range(5)
        ]
        result = self.norm.run(eps)
        assert len(result) == 5
