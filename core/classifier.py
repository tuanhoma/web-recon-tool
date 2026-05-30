"""Classifier — tag Endpoints and compute risk scores."""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from models.endpoint import Endpoint


# ---------------------------------------------------------------------------
# Rule tables
# ---------------------------------------------------------------------------

# (tag, param_name_patterns)
_PARAM_TAGS: List[Tuple[str, List[str]]] = [
    ("sqli_candidate",  ["id", "user", "username", "uid", "category", "cat",
                          "item", "product", "order", "search", "query", "q",
                          "pid", "cid", "page", "offset", "limit", "sort"]),
    ("xss_candidate",   ["q", "query", "search", "s", "keyword", "redirect",
                          "url", "callback", "next", "return", "ref", "name",
                          "comment", "msg", "message", "text", "input"]),
    ("ssrf_candidate",  ["url", "redirect", "next", "return", "ref", "dest",
                          "destination", "target", "link", "site", "host",
                          "endpoint", "proxy", "forward"]),
    ("idor_candidate",  ["id", "uid", "user_id", "userid", "account",
                          "order_id", "invoice", "ticket", "doc", "file"]),
]

# (tag, path_substrings)
_PATH_TAGS: List[Tuple[str, List[str]]] = [
    ("admin",     ["admin", "dashboard", "manage", "control", "panel",
                    "administrator", "superuser", "staff"]),
    ("api",       ["/api/", "/v1/", "/v2/", "/v3/", "/graphql", "/rest/",
                    "/rpc/", "/service/"]),
    ("debug",     ["debug", "trace", "phpinfo", ".env", "test", "dev",
                    "staging", "swagger", "openapi"]),
    ("sensitive", ["backup", "config", "secret", ".git", ".svn", ".htaccess",
                    "passwd", "shadow", "id_rsa", "wp-config", "database"]),
    ("login",     ["login", "signin", "signup", "register", "auth",
                    "oauth", "sso", "password", "reset"]),
]

# Risk score weights
_SCORE: Dict[str, int] = {
    "sqli_candidate":  3,
    "xss_candidate":   3,
    "ssrf_candidate":  3,
    "idor_candidate":  3,
    "admin":           2,
    "debug":           2,
    "sensitive":       2,
    "login":           2,
    "api":             1,
    "dynamic":         1,
    "js_endpoint":     1,
}


class Classifier:
    """
    Assigns semantic tags and risk scores to each Endpoint.

    Rules applied (in order):
    1. Param-name tags  (sqli, xss, ssrf, idor)
    2. Path-substring tags (admin, api, debug, sensitive, login)
    3. Structural tags  (dynamic, js_endpoint)
    4. ``is_interesting`` flag for score ≥ 3
    """

    def run(self, endpoints: List[Endpoint]) -> List[Endpoint]:
        return [self._classify(ep) for ep in endpoints]

    # ------------------------------------------------------------------

    def _classify(self, ep: Endpoint) -> Endpoint:
        tags: List[str] = list(ep.tags)  # preserve existing (e.g. js_endpoint)
        path_lower = ep.path.lower()

        # 1. Param-name tags
        param_set = {p.lower() for p in ep.params}
        for tag, keywords in _PARAM_TAGS:
            if param_set & set(keywords):
                if tag not in tags:
                    tags.append(tag)

        # 2. Path-substring tags
        for tag, substrings in _PATH_TAGS:
            if any(sub in path_lower for sub in substrings):
                if tag not in tags:
                    tags.append(tag)

        # 3. Structural tags
        if ep.params and "dynamic" not in tags:
            tags.append("dynamic")

        # 4. Risk score
        score = sum(_SCORE.get(t, 0) for t in tags)

        return ep.model_copy(update={
            "tags": tags,
            "risk_score": score,
            "is_interesting": score >= 3,
        })
