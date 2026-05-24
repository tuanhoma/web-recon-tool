"""HttpxAdapter — wraps projectdiscovery/httpx for host probing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from adapters.tools.base import BaseToolAdapter


class HttpxAdapter(BaseToolAdapter):
    """
    Runs::

        httpx -l <hosts_file> -silent -status-code -title -tech-detect
              -web-server -ip -cdn -json -o <output_file>

    Parses JSON-lines output into a list of dicts.
    """

    TOOL_NAME = "httpx"

    def _build_cmd(self, hosts_file: Path, **kwargs: Any) -> List[str]:  # type: ignore[override]
        out_file = self.output_dir / "httpx.json"
        self._output_file = out_file
        rate_limit = str(self.config.get("rate_limit", 150))
        per_host_timeout = str(self.config.get("per_host_timeout", 10))
        retries = str(self.config.get("retries", 1))
        threads = str(self.config.get("threads", 50))
        cmd = [
            "httpx",
            "-l", str(hosts_file),
            "-silent",
            "-status-code",
            "-title",
            "-tech-detect",
            "-web-server",
            "-ip",
            "-cdn",
            "-json",
            "-o", str(out_file),
            "-rate-limit", rate_limit,
            "-timeout", per_host_timeout,
            "-retries", retries,
            "-threads", threads,
        ]
        extra_flags: List[str] = self.config.get("flags", [])
        for flag in extra_flags:
            if flag not in cmd:
                cmd.append(flag)
        return cmd

    def _parse(self, raw: str) -> List[Dict[str, Any]]:
        """Parse JSON-lines from stdout or output file."""
        results: List[Dict[str, Any]] = []

        source = raw.strip()
        if not source and self._output_file and self._output_file.exists():
            source = self._output_file.read_text(encoding="utf-8")

        for line in source.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                pass

        return results
