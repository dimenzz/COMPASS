from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunLayout:
    run_dir: Path

    @property
    def run_yaml(self) -> Path:
        return self.run_dir / "run.yaml"

    @property
    def inputs(self) -> Path:
        return self.run_dir / "inputs"

    @property
    def logs(self) -> Path:
        return self.run_dir / "logs"

    @property
    def state(self) -> Path:
        return self.run_dir / "state"

    @property
    def search(self) -> Path:
        return self.run_dir / "search"

    @property
    def context(self) -> Path:
        return self.run_dir / "context"

    @property
    def stats(self) -> Path:
        return self.run_dir / "stats"

    @property
    def cases(self) -> Path:
        return self.run_dir / "cases"

    @property
    def evidence(self) -> Path:
        return self.run_dir / "evidence"

    @property
    def report(self) -> Path:
        return self.run_dir / "report"

    @property
    def tmp(self) -> Path:
        return self.run_dir / "tmp"

    def ensure(self) -> None:
        for path in (
            self.inputs,
            self.logs,
            self.state,
            self.search,
            self.context,
            self.stats,
            self.cases,
            self.evidence,
            self.report,
            self.tmp,
        ):
            path.mkdir(parents=True, exist_ok=True)
