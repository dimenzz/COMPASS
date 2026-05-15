from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import TypeVar

from rich.console import Console


T = TypeVar("T")


class CliProgress:
    def __init__(self, console: Console):
        self.console = console

    def run_step(self, label: str, action: Callable[[], T], log_path: Path | None = None) -> T:
        started = perf_counter()
        suffix = f" log={log_path}" if log_path is not None else ""
        self.console.print(f"[cyan]START[/cyan] {label}{suffix}")
        try:
            result = action()
        except Exception:
            elapsed = perf_counter() - started
            self.console.print(f"[red]FAILED[/red] {label} after {_format_duration(elapsed)}{suffix}")
            raise
        elapsed = perf_counter() - started
        self.console.print(f"[green]DONE[/green] {label} in {_format_duration(elapsed)}{suffix}")
        return result

    def run_stage(self, stage_name: str, run_dir: Path, action: Callable[[], T]) -> T:
        return self.run_step(
            label=f"stage {stage_name} run={run_dir}",
            action=action,
            log_path=run_dir / "logs" / f"{stage_name}.log",
        )


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, remaining_seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)}m{remaining_seconds:04.1f}s"
    hours, remaining_minutes = divmod(minutes, 60)
    return f"{int(hours)}h{int(remaining_minutes):02d}m{remaining_seconds:04.1f}s"
