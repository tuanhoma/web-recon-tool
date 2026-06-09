"""Entry point — ReconFlow CLI (Typer)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import List, Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table

from core.orchestrator import Orchestrator
from utils.logger import get_logger

app = typer.Typer(
    name="reconflow",
    help="[bold cyan]ReconFlow[/] — Automated Recon Aggregation Framework",
    rich_markup_mode="rich",
    add_completion=False,
)
console = Console()


def _load_config(config_path: str = "config/config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command("run")
def run_cmd(
    target: str = typer.Option(..., "-t", "--target", help="Target domain to recon"),
    config_file: str = typer.Option("config/config.yaml", "-c", "--config", help="Config file path"),
    resume: bool = typer.Option(False, "--resume", help="Resume from previous state"),
    skip: Optional[str] = typer.Option(None, "--skip", help="Comma-separated stages to skip (e.g. subfinder,amass)"),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level"),
) -> None:
    """
    Run the full recon pipeline against a target domain.

    Examples:

      python main.py run -t example.com

      python main.py run -t example.com --resume

      python main.py run -t example.com --skip subfinder,katana
    """
    cfg = _load_config(config_file)
    cfg["target"] = target

    log = get_logger("reconflow", level=log_level, log_file=Path(cfg.get("logging", {}).get("file", "output/reconflow.log")))

    skip_stages: List[str] = [s.strip() for s in skip.split(",")] if skip else []

    console.rule(f"[bold cyan]ReconFlow[/] → [yellow]{target}[/]")

    try:
        orchestrator = Orchestrator(cfg)
        asyncio.run(orchestrator.run(skip_stages=skip_stages, resume=resume))
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Interrupted by user.[/]")
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[red]✗ Fatal error:[/] {exc}")
        log.exception("Fatal error during run")
        raise typer.Exit(2)


@app.command("show")
def show_cmd(
    target: str = typer.Option(..., "-t", "--target", help="Target domain"),
    output_dir: str = typer.Option("output", "-o", "--output-dir", help="Output base directory"),
    fmt: str = typer.Option("table", "--format", help="Output format: table | json | interesting"),
    min_score: int = typer.Option(0, "--min-score", help="Minimum risk score filter"),
) -> None:
    """
    Display results from a previous recon run.

    Examples:

      python main.py show -t example.com

      python main.py show -t example.com --format interesting --min-score 3
    """
    import json as _json
    from utils.helpers import sanitize_filename

    result_file = Path(output_dir) / sanitize_filename(target) / "report.json"
    if not result_file.exists():
        console.print(f"[red]No results found at {result_file}[/]")
        raise typer.Exit(1)

    from models.endpoint import ReconResult
    result = ReconResult.model_validate_json(result_file.read_text(encoding="utf-8"))

    endpoints = [e for e in result.endpoints if e.risk_score >= min_score]

    if fmt == "json":
        console.print_json(result.model_dump_json(indent=2))
        return

    if fmt == "interesting":
        endpoints = [e for e in endpoints if e.is_interesting]

    table = Table(title=f"[cyan]{target}[/] — {len(endpoints)} endpoints", show_lines=False)
    table.add_column("URL", style="cyan", no_wrap=False, max_width=70)
    table.add_column("Status", justify="center", style="green")
    table.add_column("Score", justify="center", style="yellow")
    table.add_column("Tags", style="magenta")

    for ep in sorted(endpoints, key=lambda e: e.risk_score, reverse=True):
        status_str = str(ep.status) if ep.status else "-"
        tags_str = ", ".join(ep.tags[:4])
        table.add_row(ep.url, status_str, str(ep.risk_score), tags_str)

    console.print(table)
    console.print(
        f"\n[bold]Subdomains:[/] {len(result.subdomains)}  "
        f"[bold]Alive hosts:[/] {len(result.alive_hosts)}  "
        f"[bold]Total endpoints:[/] {len(result.endpoints)}"
    )


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
