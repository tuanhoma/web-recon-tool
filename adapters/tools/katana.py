"""KatanaAdapter — wraps projectdiscovery/katana for JS-aware crawling."""
from __future__ import annotations

from pathlib import Path
from typing import Any, List

from adapters.tools.base import BaseToolAdapter


class KatanaAdapter(BaseToolAdapter):
    """
    Runs::

        katana -list <hosts_file> -d 3 -jc -js-crawl -ef js,css,png,jpg,woff -silent -o <output>

    Returns a list of discovered URL strings.
    """

    TOOL_NAME = "katana"

    def _build_cmd(self, hosts_file: Path, depth: int = 3, **kwargs: Any) -> List[str]:  # type: ignore[override]
        out_file = self.output_dir / "katana.txt"
        self._output_file = out_file
        cmd = [
            "katana",
            "-list", str(hosts_file),
            "-d", str(depth),
            "-jc",              # JavaScript crawling
            "-js-crawl",
            "-ef", "js,css,png,jpg,woff,gif,ico,svg,ttf,eot",
            "-silent",
            "-o", str(out_file),
        ]
        extra_flags: List[str] = self.config.get("flags", [])
        for flag in extra_flags:
            if flag not in cmd:
                cmd.append(flag)
        return cmd

    def _parse(self, raw: str) -> List[str]:
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        if not lines and self._output_file and self._output_file.exists():
            lines = [
                l.strip()
                for l in self._output_file.read_text(encoding="utf-8").splitlines()
                if l.strip()
            ]
        return list(dict.fromkeys(lines))
