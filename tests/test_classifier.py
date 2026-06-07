"""Tests for core/classifier.py"""
import pytest
from models.endpoint import Endpoint
from core.classifier import Classifier


def _ep(path="/", params=None, tags=None) -> Endpoint:
    return Endpoint(
        url=f"https://example.com{path}",
        scheme="https",
        host="example.com",
        path=path,
        params=params or [],
        tags=tags or [],
    )


class TestClassifier:
    def setup_method(self):
        self.clf = Classifier()

    # --- param-based tags ---

    def test_sqli_candidate_on_id_param(self):
        ep = _ep("/products", params=["id"])
        result = self.clf.run([ep])[0]
        assert "sqli_candidate" in result.tags

    def test_xss_candidate_on_search_param(self):
        ep = _ep("/search", params=["q"])
        result = self.clf.run([ep])[0]
        assert "xss_candidate" in result.tags

    def test_ssrf_candidate_on_url_param(self):
        ep = _ep("/redirect", params=["url"])
        result = self.clf.run([ep])[0]
        assert "ssrf_candidate" in result.tags

    def test_idor_candidate_on_user_id(self):
        ep = _ep("/profile", params=["user_id"])
        result = self.clf.run([ep])[0]
        assert "idor_candidate" in result.tags

    # --- path-based tags ---

    def test_admin_tag_on_admin_path(self):
        ep = _ep("/admin/users")
        result = self.clf.run([ep])[0]
        assert "admin" in result.tags

    def test_api_tag_on_api_path(self):
        ep = _ep("/api/v1/users")
        result = self.clf.run([ep])[0]
        assert "api" in result.tags

    def test_debug_tag_on_phpinfo(self):
        ep = _ep("/phpinfo.php")
        result = self.clf.run([ep])[0]
        assert "debug" in result.tags

    def test_sensitive_tag_on_git(self):
        ep = _ep("/.git/config")
        result = self.clf.run([ep])[0]
        assert "sensitive" in result.tags

    # --- risk score ---

    def test_risk_score_increases_with_tags(self):
        ep_low  = _ep("/about")
        ep_high = _ep("/admin/users", params=["id", "q"])
        r_low  = self.clf.run([ep_low])[0]
        r_high = self.clf.run([ep_high])[0]
        assert r_high.risk_score > r_low.risk_score

    def test_is_interesting_when_score_gte_3(self):
        ep = _ep("/api/search", params=["q", "id"])
        result = self.clf.run([ep])[0]
        assert result.is_interesting is True

    def test_not_interesting_when_score_lt_3(self):
        ep = _ep("/static/style.css")
        result = self.clf.run([ep])[0]
        assert result.is_interesting is False

    # --- dynamic tag ---

    def test_dynamic_tag_when_has_params(self):
        ep = _ep("/page", params=["page"])
        result = self.clf.run([ep])[0]
        assert "dynamic" in result.tags
