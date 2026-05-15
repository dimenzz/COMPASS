# Discovery Case Studies

## Sources

* NAG/Cas9 case: https://www.nature.com/articles/s41586-024-07486-x
* TIGR-Tas case: https://doi.org/10.1126/science.adv9789 and https://pubmed.ncbi.nlm.nih.gov/40014690/

## Pattern 1: NAG-associated Cas9 systems

The Nature paper is a strong template for COMPASS because the discovery did not begin from sequence novelty alone. It began from a genomic-context anomaly around known CRISPR-Cas systems: unusually large Cas9 loci and recurrent accessory genes near those loci.

Transferable workflow:

1. Collect a broad homolog set for the seed protein family.
2. Compare architecture-level features across homologs: size, domain composition, insertion regions, and accessory-gene presence.
3. Identify neighbor proteins that are enriched in a subset, then stratify the seed family by the neighbor signature.
4. Compare context signatures to seed subfamily structure, not only to the whole seed family.
5. Use structure prediction / docking / co-folding as mechanistic evidence for seed-neighbor interaction.
6. Output a biological hypothesis framed as "neighbor X modulates seed Y by mechanism Z", then nominate experiments.

COMPASS implication:

* Co-localization scoring should not be only "which neighbor is most frequent near all hits". It should also ask which neighbor distinguishes a subfamily, size class, or domain-architecture class.
* Candidate novelty should include "known seed protein gains unexpected partner/function" as well as "unknown protein family near known system".

## Pattern 2: TIGR-Tas systems

The TIGR-Tas paper is the clearest blueprint for remote-homology-driven discovery.

Key computational steps reported:

1. Start from a functionally meaningful subdomain: the SpCas9 guide-RNA-interaction region.
2. Use structural similarity to jump from Cas9 RBD to IS110 RBD.
3. Use the smaller IS110 RBD as a second seed because it is a simpler least-common-denominator domain.
4. Search structural databases using Foldseek and DALI.
5. Mine Nop-domain-containing proteins at large scale.
6. Fold representatives and structurally filter candidates.
7. Embed aligned domain segments using ESM2 15B, compute cosine similarities, and apply Leiden community detection.
8. Inspect communities to find a distinct Nop-domain family.
9. Analyze genomic context and discover tandem interspaced guide RNA arrays around the candidate proteins.
10. Revisit nearby proteins and identify sub-contexts such as TasA with a ParB-like partner.

Concrete parameters from the paper that are useful defaults:

* Structural search of Cas9 RBD hits retained DALI score greater than 5 for the initial bridge.
* Candidate representatives were folded and filtered by structural similarity to the Nop region.
* Domain-segment embeddings were generated from ESM2 15B final-layer vectors.
* Leiden clustering used cosine similarity and a resolution parameter of 0.5.
* Genomic vicinity analysis used genes within 5 kb of `tas` genes, clustered at 50% identity and 70% coverage.
* The reported TIGR family contained 2,200 representative members covering 21,385 proteins.

COMPASS implication:

* The seed should be allowed to be a full protein or a selected domain interval.
* The pipeline must preserve aligned-domain coordinates, because clustering on the relevant subdomain can reveal families hidden by full-length architecture variation.
* Array and ncRNA discovery cannot be an afterthought. For RNA-guided/mobile/defense systems, the noncoding context may be the key signal.
* The final report should separate "statistical discovery", "mechanistic analogy", "evolutionary model", and "experimental proposal".
