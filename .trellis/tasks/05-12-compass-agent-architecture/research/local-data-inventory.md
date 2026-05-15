# Local Data Inventory

## Sources inspected

* `data/data_manifests/genome_manifest.csv`
* `data/data_manifests/protein_manifest.csv`
* `/mnt/nfs/share/MGnify/all_data/proteins.db`
* `/mnt/nfs/share/MGnify/all_data/clusters.db`
* `/mnt/nfs/share/MGnify/all_data/mmseqs_db`

## Current assets

* Genome manifest rows: 481,694.
* Protein manifest rows: 481,694.
* `proteins.db` size: 257 GB.
* `clusters.db` size: 217 GB.
* MMseqs database directory size: 271 GB.
* `proteins.db` metadata:
  * `total_proteins`: 1,033,056,892.
  * `total_contigs`: 96,158,961.
  * `total_mags`: 481,706.
  * `build_date`: 2026-01-04.

## Schema

`proteins.db` contains:

* `proteins(protein_id PRIMARY KEY, contig_id, mag_id, start, end, strand, length, product, gene_name, locus_tag, pfam, interpro, kegg, cog_category, cog_id, ec_number, eggnog)`.
* `contigs(contig_id PRIMARY KEY, mag_id, length, taxonomy, environment)`.
* `metadata(key PRIMARY KEY, value)`.

Indexes:

* `idx_proteins_contig ON proteins(contig_id)`.
* `idx_proteins_mag ON proteins(mag_id)`.
* `idx_contigs_mag ON contigs(mag_id)`.

`clusters.db` contains:

* `clusters(representative_id, member_id, cluster_level, PRIMARY KEY(member_id, cluster_level))`.
* Indexes on `(representative_id, cluster_level)` and `(member_id, cluster_level)`.

MMseqs databases:

* `mmseqs_db/cluster_90/all_proteins_90`.
* `mmseqs_db/cluster_30/all_proteins_30`.

## Design implications

* The existing protein table is enough to extract protein-coding neighborhoods from a homolog list.
* Context queries currently use `idx_proteins_contig`, but `ORDER BY start` creates a temporary B-tree. For large batched context extraction, COMPASS should add or materialize an index/cache equivalent to `(contig_id, start)`.
* Protein annotations are already rich enough for first-pass neighbor summaries: Pfam, InterPro, KEGG, COG, EC, eggNOG, product text.
* The database does not directly index non-protein context features such as ncRNAs, CRISPR arrays, inverted repeats, transposon ends, att sites, or terminators. These need a separate genomic-feature track.
* Given the 1B-protein scale, agent tools must be budgeted batch jobs, not free-form SQL generated directly by the LLM.

## Recommended derived tables for COMPASS

* `protein_order(contig_id, ordinal, protein_id, start, end, strand, cluster90, cluster30, annotations_json)`.
* `protein_neighbors(seed_hit_id, neighbor_protein_id, rel_ordinal, distance_bp, same_strand, cluster90, cluster30)`.
* `context_feature(contig_id, start, end, strand, feature_type, caller, score, payload_json)`.
* `run_artifact(run_id, artifact_type, path, checksum, parameters_json)`.
* `evidence_item(run_id, candidate_id, evidence_type, source, claim, confidence, payload_json)`.
