"""Orchestrator — top-level async pipeline with resume support."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.aggregator import Aggregator
from core.classifier import Classifier
from core.deduplicator import Deduplicator
from core.exporter import Exporter
from core.normalizer import Normalizer
from models.endpoint import ReconResult
from utils.helpers import ensure_output_dir
from utils.logger import get_logger, make_progress
from utils.scope import ScopeChecker

log = get_logger("reconflow.orchestrator")


class Orchestrator:
    """
    Drives the full recon pipeline::

        subfinder → httpx → katana → [feroxbuster] → [arjun]
            → normalize → deduplicate → classify → export

    Supports:
      - **Resume**: loads ``state.json`` and skips completed stages
      - **Scope enforcement**: after every tool stage
      - **Rich progress bar**: displayed during execution
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.target: str = config.get("target", "")

        base_dir = config.get("output", {}).get("base_dir", "output")
        self.output_dir = ensure_output_dir(base_dir, self.target)
        self.state_file = self.output_dir / "state.json"

        extra_domains = config.get("scope", {}).get("extra_domains", [])
        self.scope = ScopeChecker(self.target, extra_domains)

    # ------------------------------------------------------------------

    async def run(
        self,
        skip_stages: Optional[List[str]] = None,
        resume: bool = False,
    ) -> ReconResult:
        """Execute the complete recon pipeline and return a ``ReconResult``."""
        skip = list(skip_stages or [])
        state = self._load_state() if resume else {}

        result = ReconResult(
            target=self.target,
            subdomains=state.get("subdomains", []),
            alive_hosts=state.get("alive_hosts", []),
        )

        progress = make_progress()

        with progress:
            # ── Stage A: Tool Aggregation ─────────────────────────────
            task_agg = progress.add_task("🔍 Aggregating tools…", total=5)
            aggregator = Aggregator(
                target=self.target,
                output_dir=self.output_dir,
                config=self.config,
                scope=self.scope,
                skip_stages=skip,
                resume=resume,
            )
            subdomains, alive_hosts, raw_endpoints = await aggregator.run()
            result.subdomains = subdomains
            result.alive_hosts = alive_hosts
            progress.update(task_agg, completed=5)

            # ── Stage B: Normalize ────────────────────────────────────
            task_norm = progress.add_task("⚙️  Normalising…", total=len(raw_endpoints))
            normalizer = Normalizer()
            normalised = normalizer.run(raw_endpoints)
            progress.update(task_norm, completed=len(raw_endpoints))

            # ── Stage C: Deduplicate ──────────────────────────────────
            task_dedup = progress.add_task("🗂  Deduplicating…", total=len(normalised))
            deduplicator = Deduplicator()
            unique = deduplicator.run(normalised)
            progress.update(task_dedup, completed=len(normalised))

            # ── Stage D: Classify ─────────────────────────────────────
            task_cls = progress.add_task("🏷  Classifying…", total=len(unique))
            classifier = Classifier()
            classified = classifier.run(unique)
            progress.update(task_cls, completed=len(unique))

            result.endpoints = classified
            result.finished_at = datetime.now(timezone.utc)

            # ── Stage E: Export ───────────────────────────────────────
            task_exp = progress.add_task("💾  Exporting…", total=4)
            exporter = Exporter(self.output_dir)
            exporter.export_all(result)
            progress.update(task_exp, completed=4)

        # Persist state for resume
        self._save_state(result)

        # Summary
        interesting = [e for e in result.endpoints if e.is_interesting]
        log.info(
            f"[bold green]✅ Done![/] "
            f"Subdomains: {len(result.subdomains)} | "
            f"Endpoints: {len(result.endpoints)} | "
            f"Interesting: {len(interesting)}"
        )
        log.info(f"[dim]Output → {self.output_dir}[/]")

        return result

    # ------------------------------------------------------------------

    def _load_state(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_state(self, result: ReconResult) -> None:
        state = {
            "target": result.target,
            "subdomains": result.subdomains,
            "alive_hosts": result.alive_hosts,
            "endpoint_count": len(result.endpoints),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.state_file.write_text(
                json.dumps(state, indent=2), encoding="utf-8"
            )
        except OSError as e:
            log.warning(f"Could not save state: {e}")
