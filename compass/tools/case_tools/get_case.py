from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from compass.artifacts.ids import parse_case_id
from compass.artifacts.layout import RunLayout
from compass.artifacts.readers import read_jsonl, read_tsv
from compass.config.loader import read_run_metadata
from compass.config.schema import RunMetadata
from compass.data.repositories.manifests import ManifestRepository
from compass.pipeline.stages.specs import STAGE_SPECS


class CaseToolError(ValueError):
    """Raised when a case-level tool receives an invalid object reference."""


@dataclass(frozen=True)
class GetCaseRequest:
    run_dir: Path
    case_id: str


@dataclass(frozen=True)
class SequenceWindowRequest:
    run_dir: Path
    case_id: str
    target_region: str = "locus"
    flank_bp: int = 500


def get_case(request: GetCaseRequest) -> dict:
    store = CaseArtifactStore.from_run_dir(request.run_dir)
    return store.get_case_card(request.case_id)


class CaseArtifactStore:
    def __init__(
        self,
        layout: RunLayout,
        metadata: RunMetadata,
        cases: list[dict],
        loci: list[dict[str, str]],
        neighbors: list[dict[str, str]],
        diagrams: list[dict],
    ):
        self.layout = layout
        self.metadata = metadata
        self._cases_by_id = {row["case_id"]: row for row in cases}
        self._loci_by_id = {row.get("locus_id", ""): row for row in loci}
        self._neighbors_by_id = {row.get("neighbor_instance_id", ""): row for row in neighbors}
        self._diagrams_by_case_id = {row.get("case_id", ""): row for row in diagrams}

    @classmethod
    def from_run_dir(cls, run_dir: Path, cases_path: Path | None = None) -> "CaseArtifactStore":
        layout = RunLayout(run_dir)
        metadata = read_run_metadata(layout.run_yaml)
        resolved_cases_path = cases_path or (layout.run_dir / STAGE_SPECS["select-cases"].outputs["cases"])
        loci_path = layout.run_dir / STAGE_SPECS["context"].outputs["loci"]
        neighbors_path = layout.run_dir / STAGE_SPECS["context"].outputs["context_neighbors"]
        diagrams_path = layout.run_dir / STAGE_SPECS["select-cases"].outputs["locus_diagrams"]
        for required_path in (resolved_cases_path, loci_path, neighbors_path, diagrams_path):
            if not required_path.exists():
                raise FileNotFoundError(f"Missing case-tool artifact: {required_path}")
        return cls(
            layout=layout,
            metadata=metadata,
            cases=read_jsonl(resolved_cases_path),
            loci=read_tsv(loci_path),
            neighbors=read_tsv(neighbors_path),
            diagrams=read_jsonl(diagrams_path),
        )

    def list_case_ids(self) -> list[str]:
        return sorted(self._cases_by_id)

    def get_case_card(self, case_id: str) -> dict:
        self._validate_case_id(case_id)
        case = self._cases_by_id.get(case_id)
        if case is None:
            raise CaseToolError(f"Unknown case_id for run {self.metadata.run_name}: {case_id}")
        locus = self._loci_by_id.get(case.get("locus_id", ""), {})
        neighbor = self._neighbors_by_id.get(case.get("neighbor_instance_id", ""), {})
        diagram = self._diagrams_by_case_id.get(case_id, {})
        return {
            "case_id": case_id,
            "run_id": self.metadata.run_name,
            "seed_homolog": {
                "homolog_id": case.get("homolog_id", ""),
                "protein_id": case.get("seed_protein_id", ""),
                "cluster90_id": locus.get("cluster90_id", ""),
                "family30_id": locus.get("cluster30_id", ""),
                "coordinates": {
                    "start": _to_int(locus.get("start")),
                    "end": _to_int(locus.get("end")),
                    "strand": locus.get("strand", ""),
                },
            },
            "neighbor": {
                "neighbor_instance_id": case.get("neighbor_instance_id", ""),
                "protein_id": case.get("neighbor_protein_id", ""),
                "neighbor_90_rep": neighbor.get("neighbor_90_rep", ""),
                "neighbor_family_id": case.get("neighbor_30_family", ""),
                "coordinates": case.get("coordinates", {}),
                "relative_gene_index": case.get("relative_gene_index", 0),
                "distance_bp": case.get("distance_bp", 0),
            },
            "locus": {
                "locus_id": case.get("locus_id", ""),
                "contig_id": case.get("contig_id", ""),
                "mag_id": locus.get("mag_id", ""),
                "taxonomy": locus.get("taxonomy", ""),
                "environment": locus.get("environment", ""),
            },
            "annotations": {
                "seed": {
                    "product": locus.get("product", ""),
                    "pfam": locus.get("pfam", ""),
                    "interpro": locus.get("interpro", ""),
                },
                "neighbor": case.get("annotation_payload", {}),
            },
            "locus_diagram": diagram,
            "available_sequence_tools": ["get_case", "scan_case_features"],
        }

    def get_sequence_window(self, request: SequenceWindowRequest) -> dict:
        if request.flank_bp < 50 or request.flank_bp > 5000:
            raise CaseToolError("flank_bp must be between 50 and 5000")
        case_card = self.get_case_card(request.case_id)
        region = _target_region(case_card, request.target_region, request.flank_bp)
        sequence, warnings = self._load_sequence(
            mag_id=case_card["locus"]["mag_id"],
            contig_id=case_card["locus"]["contig_id"],
            start=region["start"],
            end=region["end"],
        )
        return {
            "case_id": request.case_id,
            "target_region": request.target_region,
            "scanned_region": {
                "contig_id": case_card["locus"]["contig_id"],
                "start": region["start"],
                "end": region["end"],
                "strand": region["strand"],
            },
            "sequence": sequence,
            "warnings": warnings,
        }

    def _validate_case_id(self, case_id: str) -> None:
        try:
            parse_case_id(case_id, expected_run_id=self.metadata.run_name)
        except ValueError as exc:
            raise CaseToolError(str(exc)) from exc

    def _load_sequence(self, mag_id: str, contig_id: str, start: int, end: int) -> tuple[str, list[str]]:
        warnings: list[str] = []
        manifest = ManifestRepository(self.metadata.config.database.genome_manifest)
        genome_path = manifest.get_path(mag_id)
        if genome_path is None:
            return "", [f"No genome FASTA path found for mag_id {mag_id} in configured genome_manifest"]
        if not genome_path.exists():
            return "", [f"Genome FASTA path does not exist: {genome_path}"]
        for record_id, record_sequence in _iter_fasta_records(genome_path):
            if _matches_contig(record_id, contig_id):
                clipped_start = max(1, start)
                clipped_end = min(len(record_sequence), end)
                if clipped_start > clipped_end:
                    return "", [f"Requested region is outside contig {contig_id}"]
                return record_sequence[clipped_start - 1 : clipped_end].upper(), warnings
        return "", [f"Contig {contig_id} was not found in genome FASTA {genome_path}"]


def _target_region(case_card: dict, target_region: str, flank_bp: int) -> dict[str, int | str]:
    seed = case_card["seed_homolog"]["coordinates"]
    neighbor = case_card["neighbor"]["coordinates"]
    seed_start = _to_int(seed.get("start"))
    seed_end = _to_int(seed.get("end"))
    neighbor_start = _to_int(neighbor.get("neighbor_start"))
    neighbor_end = _to_int(neighbor.get("neighbor_end"))
    neighbor_strand = str(neighbor.get("neighbor_strand", ""))

    if target_region == "locus":
        start = min(seed_start, neighbor_start) - flank_bp
        end = max(seed_end, neighbor_end) + flank_bp
    elif target_region == "intergenic_seed_neighbor":
        start = min(seed_end, neighbor_end) + 1
        end = max(seed_start, neighbor_start) - 1
    elif target_region == "seed_upstream":
        start, end = _flank(seed_start, seed_end, str(seed.get("strand", "")), flank_bp, upstream=True)
    elif target_region == "seed_downstream":
        start, end = _flank(seed_start, seed_end, str(seed.get("strand", "")), flank_bp, upstream=False)
    elif target_region == "neighbor_upstream":
        start, end = _flank(neighbor_start, neighbor_end, neighbor_strand, flank_bp, upstream=True)
    elif target_region == "neighbor_downstream":
        start, end = _flank(neighbor_start, neighbor_end, neighbor_strand, flank_bp, upstream=False)
    else:
        raise CaseToolError(f"Unsupported target_region: {target_region}")
    return {"start": max(1, start), "end": max(1, end), "strand": neighbor_strand}


def _flank(start: int, end: int, strand: str, flank_bp: int, upstream: bool) -> tuple[int, int]:
    is_reverse = strand == "-"
    take_left = upstream != is_reverse
    if take_left:
        return start - flank_bp, start - 1
    return end + 1, end + flank_bp


def _matches_contig(record_id: str, contig_id: str) -> bool:
    return record_id == contig_id or record_id.split()[0] == contig_id


def _iter_fasta_records(path: Path):
    record_id = ""
    chunks: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if record_id:
                    yield record_id, "".join(chunks)
                record_id = line[1:].split()[0]
                chunks = []
            else:
                chunks.append(line)
    if record_id:
        yield record_id, "".join(chunks)


def _to_int(value: object) -> int:
    if value in (None, ""):
        return 0
    return int(float(value))
