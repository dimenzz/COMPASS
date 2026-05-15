from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from compass.artifacts.ids import make_feature_id, parse_case_id
from compass.tools.case_tools.get_case import CaseArtifactStore, SequenceWindowRequest


@dataclass(frozen=True)
class FeatureScanRequest:
    run_dir: Path
    case_id: str
    feature_types: tuple[str, ...] = ("direct_repeat", "inverted_repeat", "tandem_repeat", "motif")
    target_region: str = "locus"
    flank_bp: int = 500


def scan_case_features(request: FeatureScanRequest) -> dict:
    store = CaseArtifactStore.from_run_dir(request.run_dir)
    window = store.get_sequence_window(
        SequenceWindowRequest(
            run_dir=request.run_dir,
            case_id=request.case_id,
            target_region=request.target_region,
            flank_bp=request.flank_bp,
        )
    )
    warnings = list(window["warnings"])
    features: list[dict] = []
    sequence = window["sequence"]
    if sequence:
        for feature_type in request.feature_types:
            features.extend(_scan_feature_type(sequence, window["scanned_region"], request.case_id, feature_type))
    else:
        warnings.append("No nucleotide sequence was available; sequence feature scanners were not run")
    return {
        "scan_id": f"{request.case_id}:scan:{request.target_region}",
        "case_id": request.case_id,
        "scanned_region": window["scanned_region"],
        "features": [_with_feature_id(request.case_id, index, feature) for index, feature in enumerate(features, start=1)],
        "warnings": warnings,
    }


def _scan_feature_type(sequence: str, region: dict, case_id: str, feature_type: str) -> list[dict]:
    if feature_type == "low_complexity":
        return _scan_low_complexity(sequence, region)
    if feature_type == "tandem_repeat":
        return _scan_tandem_repeats(sequence, region)
    if feature_type == "direct_repeat":
        return _scan_direct_repeats(sequence, region)
    if feature_type == "inverted_repeat":
        return _scan_inverted_repeats(sequence, region)
    if feature_type == "motif":
        return []
    return [
        {
            "case_id": case_id,
            "feature_type": feature_type,
            "start": int(region["start"]),
            "end": int(region["start"]),
            "strand": ".",
            "score": 0.0,
            "sequence": "",
            "summary": f"Unsupported feature type requested: {feature_type}",
            "caller": "scan_case_features",
            "parameters": {},
        }
    ]


def _scan_low_complexity(sequence: str, region: dict) -> list[dict]:
    features = []
    index = 0
    while index < len(sequence):
        end = index + 1
        while end < len(sequence) and sequence[end] == sequence[index]:
            end += 1
        run_length = end - index
        if run_length >= 8:
            features.append(_feature("low_complexity", region, index, end, sequence[index:end], run_length, f"Homopolymer run length {run_length}"))
        index = end
    return features[:20]


def _scan_tandem_repeats(sequence: str, region: dict) -> list[dict]:
    features = []
    for unit_len in range(3, 13):
        index = 0
        while index + unit_len * 3 <= len(sequence):
            unit = sequence[index : index + unit_len]
            copies = 1
            while sequence[index + copies * unit_len : index + (copies + 1) * unit_len] == unit:
                copies += 1
            if copies >= 3:
                end = index + copies * unit_len
                features.append(_feature("tandem_repeat", region, index, end, sequence[index:end], copies, f"Tandem repeat unit {unit} with {copies} copies"))
                index = end
            else:
                index += 1
    return features[:20]


def _scan_direct_repeats(sequence: str, region: dict) -> list[dict]:
    features = []
    seen: dict[str, int] = {}
    for kmer_len in range(12, 7, -1):
        seen.clear()
        for index in range(0, len(sequence) - kmer_len + 1):
            kmer = sequence[index : index + kmer_len]
            if "N" in kmer:
                continue
            previous = seen.get(kmer)
            if previous is not None and index - previous >= kmer_len:
                features.append(
                    _feature(
                        "direct_repeat",
                        region,
                        previous,
                        index + kmer_len,
                        kmer,
                        kmer_len,
                        f"Exact direct repeat length {kmer_len} at offsets {previous} and {index}",
                    )
                )
                if len(features) >= 20:
                    return features
            seen.setdefault(kmer, index)
    return features


def _scan_inverted_repeats(sequence: str, region: dict) -> list[dict]:
    features = []
    for kmer_len in range(12, 7, -1):
        for index in range(0, len(sequence) - kmer_len + 1):
            kmer = sequence[index : index + kmer_len]
            reverse = _reverse_complement(kmer)
            search_start = index + kmer_len
            search_end = min(len(sequence), index + kmer_len + 200)
            partner = sequence.find(reverse, search_start, search_end)
            if partner != -1:
                features.append(
                    _feature(
                        "inverted_repeat",
                        region,
                        index,
                        partner + kmer_len,
                        kmer,
                        kmer_len,
                        f"Exact inverted repeat arm length {kmer_len} with spacer {partner - index - kmer_len}",
                        strand="+/-",
                    )
                )
                if len(features) >= 20:
                    return features
    return features


def _feature(
    feature_type: str,
    region: dict,
    offset_start: int,
    offset_end: int,
    sequence: str,
    score: float,
    summary: str,
    strand: str = ".",
) -> dict:
    absolute_start = int(region["start"]) + offset_start
    absolute_end = int(region["start"]) + offset_end - 1
    return {
        "feature_type": feature_type,
        "contig_id": region["contig_id"],
        "start": absolute_start,
        "end": absolute_end,
        "strand": strand,
        "score": score,
        "sequence": sequence,
        "summary": summary,
        "caller": "scan_case_features",
        "parameters": {},
    }


def _with_feature_id(case_id: str, index: int, feature: dict) -> dict:
    parsed = parse_case_id(case_id)
    global_index = (parsed.index - 1) * 1000 + index
    return {"feature_id": make_feature_id(parsed.run_id, global_index), "case_id": case_id, **feature}


def _reverse_complement(sequence: str) -> str:
    return sequence.translate(str.maketrans("ACGTNacgtn", "TGCANtgcan"))[::-1].upper()
