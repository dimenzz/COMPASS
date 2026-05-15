from __future__ import annotations


CODE_DEFAULTS = {
    "database": {
        "proteins_db": "/mnt/nfs/share/MGnify/all_data/proteins.db",
        "clusters_db": "/mnt/nfs/share/MGnify/all_data/clusters.db",
        "mmseqs_db": "/mnt/nfs/share/MGnify/all_data/mmseqs_db/cluster_90/all_proteins_90",
        "family30_background": "/mnt/nfs/share/MGnify/all_data/family30_background.tsv",
        "family30_background_meta": "/mnt/nfs/share/MGnify/all_data/family30_background.meta.json",
        "genome_manifest": "data/data_manifests/genome_manifest.csv",
        "protein_manifest": "data/data_manifests/protein_manifest.csv",
    },
    "context": {
        "upstream_genes": 10,
        "downstream_genes": 10,
        "max_distance_bp": 20000,
    },
    "search": {
        "sensitivity": 5.7,
        "evalue": 1.0e-3,
        "max_seqs": 300,
    },
    "enrichment": {
        "q_value": 0.05,
        "fold_enrichment": 5.0,
        "support_contexts": 5,
        "observed_frequency": 0.05,
        "min_subgroup_size": 10,
        "min_subgroup_support_contexts": 3,
        "subgroup_specificity_q_value": 0.05,
        "subgroup_specificity_odds_ratio": 3.0,
        "max_subgroup_neighbors_for_report": 20,
        "enable_context_signature_enrichment": False,
    },
    "agent": {
        "max_families_for_llm": 20,
        "cases_per_family": 10,
        "scan_case_features_per_family": 3,
        "max_revision_rounds": 1,
    },
    "llm": {
        "enabled": False,
        "provider": "openai",
        "model": "gpt-4.1",
        "api_key_env": "OPENAI_API_KEY",
        "temperature": 0.2,
        "max_output_tokens": 4096,
        "structured_outputs": True,
    },
    "artifacts": {
        "output_root": "runs",
    },
}
