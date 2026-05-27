"""ArjunAdapter — wraps arjun for HTTP parameter discovery."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from adapters.tools.base import BaseToolAdapter


class ArjunAdapter(BaseToolAdapter):
    """
    Runs::

        arjun -u <url> -m GET -t 5 --delay 0.2 -oJ <output_file>

    Only invoked selectively on API endpoints and dynamic routes.
    Returns a list of discovered parameter dicts.
    """

    TOOL_NAME = "arjun"

    def _build_cmd(  # type: ignore[override]
        self,
        url: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> List[str]:
        out_file = self.output_dir / f"arjun_{self._safe_name(url)}.json"
        self._output_file = out_file

        threads = str(self.config.get("threads", 5))
        delay = str(self.config.get("delay", 0.2))

        cmd = [
            "arjun",
            "-u", url,
            "-m", method,
            "-t", threads,
            "--delay", delay,
            "-oJ", str(out_file),
        ]
        extra_flags: List[str] = self.config.get("flags", [])
        for flag in extra_flags:
            if flag not in cmd:
                cmd.append(flag)
        return cmd

    def _parse(self, raw: str) -> List[Dict[str, Any]]:
        # Arjun writes JSON to file; stdout is human-readable logs
        if self._output_file and self._output_file.exists():
            try:
                data = json.loads(self._output_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    return [data]
            except json.JSONDecodeError:
                pass
        return []

    @staticmethod
    def _safe_name(url: str) -> str:
        import re
        return re.sub(r"[^\w]", "_", url)[:40]
