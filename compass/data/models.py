from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchHit:
    query: str
    target: str
    pident: float
    alnlen: int
    evalue: float
    bits: float
    qcov: float | None = None
    tcov: float | None = None


@dataclass(frozen=True)
class ProteinRecord:
    protein_id: str
    contig_id: str = ""
    mag_id: str = ""
    start: int | None = None
    end: int | None = None
    strand: str = ""
    length: int | None = None
    product: str = ""
    gene_name: str = ""
    locus_tag: str = ""
    pfam: str = ""
    interpro: str = ""
    kegg: str = ""
    cog_category: str = ""
    cog_id: str = ""
    ec_number: str = ""
    eggnog: str = ""
    taxonomy: str = ""
    environment: str = ""


@dataclass(frozen=True)
class ContextWindowItem:
    seed_protein_id: str
    neighbor: ProteinRecord
    relative_gene_index: int
    distance_bp: int
