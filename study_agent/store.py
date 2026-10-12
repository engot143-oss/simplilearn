"""Load and save the learner profile, curriculum, and progress log."""

from __future__ import annotations

import json
from pathlib import Path


class Store:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.data = root / "data"
        self.snapshots = self.data / "snapshots"

    def read_json(self, name: str) -> dict:
        path = self.data / name
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def write_json(self, name: str, payload: dict) -> None:
        path = self.data / name
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def curriculum(self) -> dict:
        return self.read_json("curriculum.json")

    def profile(self) -> dict:
        return self.read_json("profile.json")

    def progress(self) -> dict:
        return self.read_json("progress.json")

    def save_progress(self, payload: dict) -> None:
        self.write_json("progress.json", payload)

    def snapshot(self, source_id: str) -> dict | None:
        path = self.snapshots / f"{source_id}.json"
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def save_snapshot(self, source_id: str, payload: dict) -> None:
        self.snapshots.mkdir(parents=True, exist_ok=True)
        path = self.snapshots / f"{source_id}.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def save_report(self, report: str) -> None:
        (self.data / "latest_report.md").write_text(report, encoding="utf-8")
