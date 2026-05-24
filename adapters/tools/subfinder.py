"""SubfinderAdapter — wraps subfinder for passive subdomain enumeration."""
from __future__ import annotations

from pathlib import Path
from typing import Any, List

from adapters.tools.base import BaseToolAdapter


class SubfinderAdapter(BaseToolAdapter):
    """
    Runs::

        subfinder -d <target> -all -silent -o <output_file>
    """

    TOOL_NAME = "subfinder"

    def _build_cmd(self, target: str, **kwargs: Any) -> List[str]:  # type: ignore[override]
        out_file = self.output_dir / "subdomains.txt"
        self._output_file = out_file
        cmd = [
            "subfinder",
            "-d", target,
            "-all",
            "-silent",
            "-o", str(out_file),
        ]
        extra_flags: List[str] = self.config.get("flags", [])
        for flag in extra_flags:
            if flag not in cmd:
                cmd.append(flag)
        return cmd

    def _parse(self, raw: str) -> List[str]:
        """Return unique, non-empty subdomain lines from stdout."""
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        # Also read from output file if stdout was empty (subfinder -o)
        if not lines and self._output_file and self._output_file.exists():
            lines = [
                l.strip()
                for l in self._output_file.read_text(encoding="utf-8").splitlines()
                if l.strip()
            ]
        return list(dict.fromkeys(lines))  # deduplicate, preserve order