"""FeroxbusterAdapter — wraps feroxbuster for directory/path brute-forcing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from adapters.tools.base import BaseToolAdapter


class FeroxbusterAdapter(BaseToolAdapter):
    """
    Runs::

        feroxbuster -u <url> -w <wordlist> -C 404,403,400 -t 50 --silent
                    --json -o <output_file>

    Only invoked on *interesting* hosts (admin, api, login paths detected).
    """

    TOOL_NAME = "feroxbuster"

    def _build_cmd(  # type: ignore[override]
        self,
        url: str,
        wordlist: Optional[str] = None,
        **kwargs: Any,
    ) -> List[str]:
        out_file = self.output_dir / f"ferox_{self._safe_name(url)}.json"
        self._output_file = out_file

        wl = wordlist or self.config.get("wordlist", "config/wordlists/dirs.txt")
        threads = str(self.config.get("threads", 50))
        filter_codes = self.config.get("filter_codes", "404,403,400")

        cmd = [
            "feroxbuster",
            "-u", url,
            "-w", wl,
            "-C", filter_codes,
            "-t", threads,
            "--silent",
            "--json",
            "-o", str(out_file),
        ]
        extra_flags: List[str] = self.config.get("flags", [])
        for flag in extra_flags:
            if flag not in cmd:
                cmd.append(flag)
        return cmd

    def _parse(self, raw: str) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        source = raw.strip()
        if not source and self._output_file and self._output_file.exists():
            source = self._output_file.read_text(encoding="utf-8")
        for line in source.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                # feroxbuster emits type="response" for actual hits
                if obj.get("type") == "response":
                    results.append(obj)
            except json.JSONDecodeError:
                pass
        return results

    @staticmethod
    def _safe_name(url: str) -> str:
        import re
        return re.sub(r"[^\w]", "_", url)[:40]
