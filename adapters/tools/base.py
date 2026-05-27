"""adapters/tools/base.py — Async abstract base class for all tool wrappers."""
from __future__ import annotations

import asyncio
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("reconflow.adapter")


class BaseToolAdapter(ABC):
    """
    Abstract async wrapper for external CLI security tools.

    Subclasses must implement:
      - ``_build_cmd()``  — return the full argument list
      - ``_parse()``      — parse raw stdout / output file into results

    The ``run()`` coroutine handles process creation, timeout, and logging.
    """

    #: Override in subclass — name used for logging and rate-limiting
    TOOL_NAME: str = "tool"

    def __init__(
        self,
        output_dir: Path,
        config: Dict[str, Any] | None = None,
        timeout: int = 600,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config: Dict[str, Any] = config or {}
        self.timeout = timeout
        self._output_file: Optional[Path] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, *args: Any, **kwargs: Any) -> List[Any]:
        """
        Execute the tool and return parsed results.

        Raises:
            RuntimeError: if the tool binary is not found.
            asyncio.TimeoutError: if the tool exceeds ``self.timeout`` seconds.
        """
        binary = self._build_cmd(*args, **kwargs)[0]
        if not shutil.which(binary):
            log.warning(
                f"[yellow]⚠ {self.TOOL_NAME}[/] binary '[bold]{binary}[/]' not found — skipping."
            )
            return []

        cmd = self._build_cmd(*args, **kwargs)
        log.info(f"[cyan]▶ {self.TOOL_NAME}[/] {' '.join(str(c) for c in cmd)}")

        try:
            stdout = await self._exec(cmd)
        except asyncio.TimeoutError:
            log.error(f"[red]{self.TOOL_NAME} timed out after {self.timeout}s[/]")
            return []

        results = self._parse(stdout)
        log.info(f"[green]✔ {self.TOOL_NAME}[/] → {len(results)} results")
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _exec(self, cmd: List[str]) -> str:
        """Run *cmd* as a subprocess and return combined stdout as a string."""
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise

        if proc.returncode not in (0, 1):  # many tools exit 1 on "no results"
            err = stderr_b.decode(errors="replace").strip()
            if err:
                log.debug(f"[dim]{self.TOOL_NAME} stderr:[/] {err[:400]}")

        return stdout_b.decode(errors="replace")

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def _build_cmd(self, *args: Any, **kwargs: Any) -> List[str]:
        """Return the full command + argument list to execute."""

    @abstractmethod
    def _parse(self, raw: str) -> List[Any]:
        """Parse raw tool output into a list of result objects."""
