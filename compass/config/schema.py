from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class DatabaseConfig(BaseModel):
    proteins_db: Path
    clusters_db: Path
    mmseqs_db: Path
    family30_background: Path | None = None
    family30_background_meta: Path | None = None
    genome_manifest: Path | None = None
    protein_manifest: Path | None = None


class ContextConfig(BaseModel):
    upstream_genes: int = Field(ge=0)
    downstream_genes: int = Field(ge=0)
    max_distance_bp: int = Field(gt=0)


class SearchConfig(BaseModel):
    sensitivity: float = Field(gt=0)
    evalue: float = Field(gt=0)
    max_seqs: int = Field(gt=0)


class EnrichmentConfig(BaseModel):
    q_value: float = Field(gt=0, le=1)
    fold_enrichment: float = Field(gt=0)
    support_contexts: int = Field(ge=1)
    observed_frequency: float = Field(gt=0, le=1)
    min_subgroup_size: int = Field(default=10, ge=1)
    min_subgroup_support_contexts: int = Field(default=3, ge=1)
    subgroup_specificity_q_value: float = Field(default=0.05, gt=0, le=1)
    subgroup_specificity_odds_ratio: float = Field(default=3.0, ge=0)
    max_subgroup_neighbors_for_report: int = Field(default=20, ge=1)
    enable_context_signature_enrichment: bool = False


class AgentConfig(BaseModel):
    max_families_for_llm: int = Field(ge=0)
    cases_per_family: int = Field(ge=0)
    scan_case_features_per_family: int = Field(ge=0)
    max_revision_rounds: int = Field(ge=0)


class LlmConfig(BaseModel):
    enabled: bool
    provider: str
    model: str
    api_key_env: str
    temperature: float = Field(ge=0)
    max_output_tokens: int = Field(gt=0)
    structured_outputs: bool


class ArtifactConfig(BaseModel):
    output_root: Path


class CompassConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    database: DatabaseConfig
    context: ContextConfig
    search: SearchConfig
    enrichment: EnrichmentConfig
    agent: AgentConfig
    llm: LlmConfig
    artifacts: ArtifactConfig


class RunMetadata(BaseModel):
    run_name: str
    seed_fasta: Path
    config_files: list[Path]
    config: CompassConfig
