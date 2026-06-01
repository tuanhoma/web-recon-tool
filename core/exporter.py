"""Exporter — write ReconResult to JSON, SQLite, and TXT formats."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.endpoint import ReconResult


class Exporter:
    """
    Writes a ``ReconResult`` to the output directory in multiple formats:

    - ``report.json``         — full result (pretty-printed)
    - ``endpoints.db``        — SQLite table ``endpoints``
    - ``urls.txt``            — all endpoint URLs, one per line
    - ``interesting.txt``     — only URLs where ``is_interesting=True``
    """

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def export_all(self, result: "ReconResult") -> None:
        self.export_json(result)
        self.export_sqlite(result)
        self.export_txt(result)
        self.export_interesting_txt(result)

    def export_json(self, result: "ReconResult") -> Path:
        path = self.output_dir / "report.json"
        path.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return path

    def export_sqlite(self, result: "ReconResult") -> Path:
        path = self.output_dir / "endpoints.db"
        con = sqlite3.connect(str(path))
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS endpoints (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                url          TEXT NOT NULL,
                scheme       TEXT,
                host         TEXT,
                path         TEXT,
                method       TEXT,
                params       TEXT,
                status       INTEGER,
                title        TEXT,
                tech         TEXT,
                web_server   TEXT,
                ip           TEXT,
                is_cdn       INTEGER,
                source_tools TEXT,
                risk_score   INTEGER,
                tags         TEXT,
                is_interesting INTEGER,
                dedup_hash   TEXT,
                discovered_at TEXT
            )
        """)
        # Upsert by dedup_hash to support resume/re-export
        cur.execute("DELETE FROM endpoints WHERE 1=1")
        for ep in result.endpoints:
            cur.execute(
                """
                INSERT INTO endpoints
                  (url, scheme, host, path, method, params, status, title,
                   tech, web_server, ip, is_cdn, source_tools, risk_score,
                   tags, is_interesting, dedup_hash, discovered_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    ep.url, ep.scheme, ep.host, ep.path, ep.method,
                    json.dumps(ep.params),
                    ep.status, ep.title,
                    json.dumps(ep.tech),
                    ep.web_server, ep.ip,
                    int(ep.is_cdn),
                    json.dumps(ep.source_tools),
                    ep.risk_score,
                    json.dumps(ep.tags),
                    int(ep.is_interesting),
                    ep.dedup_hash,
                    ep.discovered_at.isoformat(),
                ),
            )
        con.commit()
        con.close()
        return path

    def export_txt(self, result: "ReconResult") -> Path:
        path = self.output_dir / "urls.txt"
        path.write_text(
            "\n".join(ep.url for ep in result.endpoints),
            encoding="utf-8",
        )
        return path

    def export_interesting_txt(self, result: "ReconResult") -> Path:
        path = self.output_dir / "interesting.txt"
        interesting = [ep.url for ep in result.endpoints if ep.is_interesting]
        path.write_text("\n".join(interesting), encoding="utf-8")
        return path
