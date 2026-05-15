from __future__ import annotations

from pathlib import Path

from compass.tools.bio_tools.mmseqs import parse_hits


def test_parse_hits_without_header(tmp_path: Path) -> None:
    hits_path = tmp_path / "hits.tsv"
    hits_path.write_text("seedA\trep1\t41.2\t120\t1e-20\t88.5\t0.74\t0.81\n", encoding="utf-8")

    hits = parse_hits(hits_path)

    assert len(hits) == 1
    assert hits[0].query == "seedA"
    assert hits[0].target == "rep1"
    assert hits[0].evalue == 1e-20
    assert hits[0].tcov == 0.81


def test_parse_hits_with_header(tmp_path: Path) -> None:
    hits_path = tmp_path / "hits.tsv"
    hits_path.write_text(
        "query\ttarget\tpident\talnlen\tevalue\tbits\tqcov\ttcov\n"
        "seedA\trep1\t41.2\t120\t1e-20\t88.5\t0.74\t0.81\n",
        encoding="utf-8",
    )

    hits = parse_hits(hits_path)

    assert len(hits) == 1
    assert hits[0].query == "seedA"
    assert hits[0].target == "rep1"
