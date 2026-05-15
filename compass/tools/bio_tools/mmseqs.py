from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from compass.artifacts.readers import read_headerless_tsv
from compass.config.schema import CompassConfig
from compass.data.models import SearchHit


MMSEQS_FORMAT_FIELDS = ["query", "target", "pident", "alnlen", "evalue", "bits", "qcov", "tcov"]
MMSEQS_FORMAT = ",".join(MMSEQS_FORMAT_FIELDS)


def run_easy_search(
    seed_fasta: Path,
    output_path: Path,
    tmp_dir: Path,
    config: CompassConfig,
    tool_log_path: Path | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "mmseqs",
        "easy-search",
        str(seed_fasta),
        str(config.database.mmseqs_db),
        str(output_path),
        str(tmp_dir),
        "--format-output",
        MMSEQS_FORMAT,
        "-s",
        str(config.search.sensitivity),
        "-e",
        str(config.search.evalue),
        "--max-seqs",
        str(config.search.max_seqs),
    ]
    if tool_log_path is None:
        subprocess.run(cmd, check=True)
    else:
        tool_log_path.parent.mkdir(parents=True, exist_ok=True)
        with tool_log_path.open("w", encoding="utf-8") as handle:
            handle.write("$ " + " ".join(cmd) + "\n\n")
            handle.flush()
            subprocess.run(cmd, check=True, stdout=handle, stderr=subprocess.STDOUT)
    return output_path


def copy_existing_hits(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return destination


def parse_hits(path: Path) -> list[SearchHit]:
    rows = read_headerless_tsv(path)
    if not rows:
        return []
    has_header = set(("query", "target")).issubset(set(rows[0]))
    data_rows = rows[1:] if has_header else rows
    fields = rows[0] if has_header else MMSEQS_FORMAT_FIELDS
    hits: list[SearchHit] = []
    for values in data_rows:
        row = {fields[index]: value for index, value in enumerate(values[: len(fields)])}
        if not row.get("target"):
            continue
        hits.append(
            SearchHit(
                query=row.get("query", ""),
                target=row["target"],
                pident=_float(row.get("pident")),
                alnlen=_int(row.get("alnlen")),
                evalue=_float(row.get("evalue")),
                bits=_float(row.get("bits")),
                qcov=_optional_float(row.get("qcov")),
                tcov=_optional_float(row.get("tcov")),
            )
        )
    return hits


def search_score_bin(hit: SearchHit | None) -> str:
    if hit is None:
        return "expanded_only"
    if hit.pident >= 50:
        return "close"
    if hit.pident >= 30:
        return "medium"
    return "remote"


def _float(value: str | None) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _optional_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _int(value: str | None) -> int:
    if value in (None, ""):
        return 0
    return int(float(value))
