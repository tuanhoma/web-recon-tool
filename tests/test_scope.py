"""Tests for utils/scope.py"""
import pytest
from utils.scope import ScopeChecker


class TestScopeChecker:
    # --- basic domain ---

    def test_exact_target_in_scope(self):
        sc = ScopeChecker("example.com")
        assert sc.is_in_scope("example.com") is True

    def test_subdomain_in_scope(self):
        sc = ScopeChecker("example.com")
        assert sc.is_in_scope("sub.example.com") is True

    def test_different_domain_out_of_scope(self):
        sc = ScopeChecker("example.com")
        assert sc.is_in_scope("evil.com") is False

    def test_partial_match_rejected(self):
        sc = ScopeChecker("example.com")
        # notexample.com must be rejected
        assert sc.is_in_scope("notexample.com") is False

    # --- URL extraction ---

    def test_url_with_path_in_scope(self):
        sc = ScopeChecker("example.com")
        assert sc.is_in_scope("https://sub.example.com/path?q=1") is True

    def test_url_different_domain_out_of_scope(self):
        sc = ScopeChecker("example.com")
        assert sc.is_in_scope("https://other.com/page") is False

    # --- wildcard ---

    def test_wildcard_matches_subdomain(self):
        sc = ScopeChecker("*.example.com")
        assert sc.is_in_scope("api.example.com") is True

    def test_wildcard_matches_base_domain(self):
        sc = ScopeChecker("*.example.com")
        assert sc.is_in_scope("example.com") is True

    # --- CIDR ---

    def test_ip_in_cidr_in_scope(self):
        sc = ScopeChecker("10.0.0.0/8")
        assert sc.is_in_scope("10.1.2.3") is True

    def test_ip_outside_cidr_out_of_scope(self):
        sc = ScopeChecker("10.0.0.0/8")
        assert sc.is_in_scope("192.168.1.1") is False

    # --- extra domains ---

    def test_extra_domain_in_scope(self):
        sc = ScopeChecker("example.com", extra_domains=["partner.io"])
        assert sc.is_in_scope("api.partner.io") is True

    # --- filter ---

    def test_filter_returns_only_in_scope(self):
        sc = ScopeChecker("example.com")
        hosts = ["sub.example.com", "evil.com", "api.example.com"]
        result = sc.filter(hosts)
        assert result == ["sub.example.com", "api.example.com"]
