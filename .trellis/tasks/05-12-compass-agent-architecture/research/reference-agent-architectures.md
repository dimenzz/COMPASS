# Reference Agent Architectures

## Sources

* STELLA: https://github.com/zaixizhang/STELLA
* CellVoyager: https://github.com/zou-group/CellVoyager

## STELLA patterns to reuse

STELLA uses a manager/dev/critic organization with a governed tool ecosystem.

Useful ideas for COMPASS:

* A manager agent decomposes the scientific objective, retrieves relevant workflow templates, and orchestrates specialist agents.
* A dev agent executes concrete computational work through tools.
* A critic agent evaluates result quality and asks for additional evidence when a result is weak.
* A tool registry stores tool manifests, dependencies, validation status, and usage statistics.
* Successful workflows are summarized into reusable skills/templates.

COMPASS adaptation:

* The manager should never directly run expensive database-scale searches. It should create a plan with explicit budgets and then call typed tools.
* The critic should be biology-aware and statistics-aware: it should check enrichment validity, multiple-testing control, annotation quality, and whether mechanistic claims exceed the evidence.
* Tool creation should be limited in v1. For reproducibility, new bioinformatics tools should be added as versioned wrappers, not dynamically generated ad hoc scripts.

## CellVoyager patterns to reuse

CellVoyager separates hypothesis generation from notebook execution and keeps an interactive, inspectable analysis trail.

Useful ideas for COMPASS:

* A `HypothesisGenerator` produces structured hypotheses, analysis plans, first-step code, and summaries.
* An executor writes and runs a live Jupyter notebook, preserving code, outputs, interpretations, and user edits.
* The system supports self-critique, incorporation of critique, and iterative next-step planning.
* Interactive mode pauses so the user can steer the analysis.

COMPASS adaptation:

* The main output for each seed-family run should be a durable run directory with a report, tables, figures, logs, and optionally an executable notebook.
* Notebook-style execution is useful for exploratory analysis, but the core search/context/statistics stages should be deterministic CLI tasks with parameter files.
* COMPASS should expose an "interactive checkpoint" after homolog discovery, after context enrichment, and before final biological hypothesis synthesis.

## Recommended COMPASS agent roles

* `RunPlanner`: validates user seed input, chooses search strategy, estimates cost, and creates a run plan.
* `SearchAgent`: runs MMseqs/Foldseek/HMM/profile searches and merges hits.
* `ContextAgent`: extracts neighborhoods, noncoding features, and taxonomic/environment metadata.
* `StatisticsAgent`: computes co-localization enrichment, subfamily-specific signatures, and controls false discovery.
* `StructureAgent`: performs domain parsing, structure prediction/search, co-folding, and interaction plausibility checks.
* `LiteratureAgent`: retrieves papers/database entries and normalizes claims into evidence items.
* `SynthesisAgent`: turns evidence items into hypotheses with confidence/caveats.
* `CriticAgent`: checks whether each claim is supported and flags missing evidence.
