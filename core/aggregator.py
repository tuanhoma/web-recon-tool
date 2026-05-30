"""Aggregator — orchestrate tool execution and aggregate raw results."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from adapters.parsers import (
    parse_arjun_results,
    parse_ferox_results,
    parse_httpx_results,
    parse_katana_results,
)
from adapters.tools.arjun import ArjunAdapter
from adapters.tools.feroxbuster import FeroxbusterAdapter
from adapters.tools.httpx import HttpxAdapter
from adapters.tools.katana import KatanaAdapter
from adapters.tools.subfinder import SubfinderAdapter
from models.endpoint import Endpoint
from utils.logger import get_logger
from utils.scope import ScopeChecker

log = get_logger("reconflow.aggregator")


class Aggregator:
    """
    Runs tool adapters **in pipeline order** and aggregates results.

    Pipeline stages:
      1. subfinder  → subdomains
      2. httpx      → alive hosts + Endpoint stubs
      3. katana     → crawled URLs → more Endpoints
      4. feroxbuster (selective) → bruteforced paths
      5. arjun      (selective) → discovered params
    """

    def __init__(
        self,
        target: str,
        output_dir: Path,
        config: Dict[str, Any],
        scope: ScopeChecker,
        skip_stages: Optional[List[str]] = None,
        resume: bool = False,
    ) -> None:
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.scope = scope
        self.skip = set(skip_stages or [])
        self.resume = resume

    # ------------------------------------------------------------------

    async def run(self) -> tuple[List[str], List[Dict[str, Any]], List[Endpoint]]:
        """
        Execute the full pipeline.

        Returns:
            (subdomains, alive_host_records, endpoints)
        """
        subdomains: List[str] = []
        alive_records: List[Dict[str, Any]] = []
        endpoints: List[Endpoint] = []

        tools_cfg = self.config.get("tools", {})

        # ── Stage 1: subfinder ──────────────────────────────────────────
        if "subfinder" not in self.skip and tools_cfg.get("subfinder", {}).get("enabled", True):
            subdomains = await self._run_subfinder()
            subdomains = self.scope.filter(subdomains)
            log.info(f"[cyan]subfinder[/] → {len(subdomains)} in-scope subdomains")
        else:
            log.info("[dim]subfinder — skipped[/]")

        # ── Stage 2: httpx ──────────────────────────────────────────────
        hosts_file = self.output_dir / "hosts.txt"
        if "httpx" not in self.skip and tools_cfg.get("httpx", {}).get("enabled", True):
            # Write hosts to file
            host_list = subdomains if subdomains else [self.target]
            hosts_file.write_text("\n".join(host_list), encoding="utf-8")
            alive_records, httpx_endpoints = await self._run_httpx(hosts_file)
            endpoints.extend(httpx_endpoints)
            log.info(f"[cyan]httpx[/] → {len(alive_records)} alive hosts")
        else:
            log.info("[dim]httpx — skipped[/]")
            # Still need hosts_file for katana
            host_list = subdomains if subdomains else [self.target]
            hosts_file.write_text("\n".join(host_list), encoding="utf-8")

        # ── Stage 3: katana ─────────────────────────────────────────────
        if "katana" not in self.skip and tools_cfg.get("katana", {}).get("enabled", True):
            katana_eps = await self._run_katana(hosts_file)
            endpoints.extend(katana_eps)
            log.info(f"[cyan]katana[/] → {len(katana_eps)} URLs crawled")
        else:
            log.info("[dim]katana — skipped[/]")

        # ── Stage 4: feroxbuster (selective) ────────────────────────────
        if "feroxbuster" not in self.skip and tools_cfg.get("feroxbuster", {}).get("enabled", False):
            interesting_hosts = self._interesting_hosts(alive_records)
            ferox_eps = await self._run_feroxbuster(interesting_hosts, tools_cfg.get("feroxbuster", {}))
            endpoints.extend(ferox_eps)
            log.info(f"[cyan]feroxbuster[/] → {len(ferox_eps)} paths found")
        else:
            log.info("[dim]feroxbuster — skipped[/]")

        # ── Stage 5: arjun (selective) ──────────────────────────────────
        if "arjun" not in self.skip and tools_cfg.get("arjun", {}).get("enabled", False):
            arjun_eps = await self._run_arjun(endpoints, tools_cfg.get("arjun", {}))
            # Merge arjun results back (param enrichment)
            endpoints.extend(arjun_eps)
            log.info(f"[cyan]arjun[/] → enriched {len(arjun_eps)} endpoints")
        else:
            log.info("[dim]arjun — skipped[/]")

        return subdomains, alive_records, endpoints

    # ------------------------------------------------------------------
    # Private stage runners
    # ------------------------------------------------------------------

    async def _run_subfinder(self) -> List[str]:
        adapter = SubfinderAdapter(
            output_dir=self.output_dir,
            config=self.config.get("tools", {}).get("subfinder", {}),
        )
        return await adapter.run(target=self.target)

    async def _run_httpx(
        self, hosts_file: Path
    ) -> tuple[List[Dict[str, Any]], List[Endpoint]]:
        httpx_cfg = self.config.get("tools", {}).get("httpx", {})
        timeout = httpx_cfg.get("timeout", 1800)  # 30 min for large subdomain lists
        adapter = HttpxAdapter(
            output_dir=self.output_dir,
            config=httpx_cfg,
            timeout=timeout,
        )
        records = await adapter.run(hosts_file=hosts_file)
        endpoints = parse_httpx_results(records)
        return records, endpoints

    async def _run_katana(self, hosts_file: Path) -> List[Endpoint]:
        katana_cfg = self.config.get("tools", {}).get("katana", {})
        timeout = katana_cfg.get("timeout", 1800)
        adapter = KatanaAdapter(
            output_dir=self.output_dir,
            config=katana_cfg,
            timeout=timeout,
        )
        lines = await adapter.run(hosts_file=hosts_file)
        return parse_katana_results(lines)

    async def _run_feroxbuster(
        self,
        urls: List[str],
        tool_cfg: Dict[str, Any],
    ) -> List[Endpoint]:
        endpoints: List[Endpoint] = []
        tasks = []
        for url in urls:
            adapter = FeroxbusterAdapter(output_dir=self.output_dir, config=tool_cfg)
            tasks.append(adapter.run(url=url))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, list):
                endpoints.extend(parse_ferox_results(res))
        return endpoints

    async def _run_arjun(
        self,
        endpoints: List[Endpoint],
        tool_cfg: Dict[str, Any],
    ) -> List[Endpoint]:
        # Run arjun only on API / dynamic endpoints
        candidates = [
            ep for ep in endpoints
            if ep.params or any(t in ep.tags for t in ("api", "dynamic"))
        ][:20]  # cap at 20 to avoid hammering

        result_eps: List[Endpoint] = []
        for ep in candidates:
            adapter = ArjunAdapter(output_dir=self.output_dir, config=tool_cfg)
            records = await adapter.run(url=ep.raw_url or ep.url, method=ep.method)
            result_eps.extend(parse_arjun_results(records))
        return result_eps

    @staticmethod
    def _interesting_hosts(alive_records: List[Dict[str, Any]]) -> List[str]:
        """Return URLs of hosts that look interesting for feroxbuster."""
        interesting_paths = {"api", "admin", "login", "dev", "dashboard"}
        result: List[str] = []
        for rec in alive_records:
            url: str = rec.get("url", "")
            if url and any(p in url.lower() for p in interesting_paths):
                result.append(url)
        return result or [rec.get("url", "") for rec in alive_records[:5]]
