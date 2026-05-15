# Project Structure and Configuration

## Decision

COMPASS should use a readable responsibility-based layout inspired by STELLA's tool registry and CellVoyager's run/execution workspace. The code should not be organized as one flat utility package.

## Proposed Layout

```text
COMPASS/
  configs/
    default.yaml

  environment.yml
  pyproject.toml

  compass/
    cli/
      main.py
      options.py

    config/
      schema.py
      loader.py
      defaults.py

    pipeline/
      run.py
      stages/
        search.py
        expand.py
        context.py
        grouping.py
        enrichment.py
        cases.py
        report.py

    data/
      models.py
      repositories/
        proteins.py
        clusters.py
        manifests.py

    artifacts/
      layout.py
      readers.py
      writers.py
      ids.py
      schemas.py
      state.py

    tools/
      registry.py
      manifests/
        scan_case_features.yaml
        get_case.yaml
      case_tools/
        get_case.py
        get_locus_diagram.py
        get_sequence_window.py
        scan_case_features.py
      bio_tools/
        mmseqs.py
        repeat_scanner.py
        motif_scanner.py

    agents/
      manager.py
      inspector.py
      hypothesis.py
      critic.py
      prompts/
        manager.md
        critic.md
        hypothesis.md

    stats/
      enrichment.py
      multiple_testing.py

    reporting/
      renderer.py
      templates/
        report.md.j2

  tests/
    unit/
    integration/
```

## Boundaries

* `pipeline/` owns deterministic workflow orchestration.
* `pipeline/stages/` owns individual reproducible stages.
* `data/repositories/` owns SQLite and manifest reads.
* `artifacts/` owns run directory layout, typed IDs, schemas, readers/writers, and stage state.
* `tools/` owns LLM-callable and bioinformatics tools.
* `agents/` owns future planning, inspection, hypothesis synthesis, and critique.
* `reporting/` owns Markdown/HTML rendering.

## Environment

Use a conda environment for the project:

```yaml
name: compass
channels:
  - conda-forge
  - bioconda
dependencies:
  - python=3.11
  - mmseqs2
  - pandas
  - scipy
  - pyyaml
  - biopython
  - typer
  - rich
  - pydantic
  - pytest
  - pip
  - pip:
      - -e .
      - litellm
      - instructor
      - openai
```

`pyproject.toml` should still define package metadata, console scripts, and test config.

## Configuration Precedence

Configuration precedence:

```text
code defaults < configs/default.yaml < user YAML (--config) < explicit CLI args
```

CLI option defaults should be `None` where possible so the CLI only overrides YAML when the user explicitly passes a value.

## Default YAML Shape

```yaml
database:
  proteins_db: /mnt/nfs/share/MGnify/all_data/proteins.db
  clusters_db: /mnt/nfs/share/MGnify/all_data/clusters.db
  mmseqs_db: /mnt/nfs/share/MGnify/all_data/mmseqs_db/cluster_90/all_proteins_90

context:
  upstream_genes: 10
  downstream_genes: 10
  max_distance_bp: 20000

search:
  sensitivity: 5.7
  evalue: 1.0e-3
  max_seqs: 300

enrichment:
  q_value: 0.05
  fold_enrichment: 5
  support_contexts: 5
  observed_frequency: 0.05

agent:
  max_families_for_llm: 20
  cases_per_family: 10
  scan_case_features_per_family: 3
  max_revision_rounds: 1

llm:
  enabled: false
  provider: openai
  model: gpt-4.1
  api_key_env: OPENAI_API_KEY
  temperature: 0.2
  max_output_tokens: 4096
  structured_outputs: true

artifacts:
  output_root: runs
```

## LLM Dependency Policy

LLM inference is a v1 feature but should remain optional at runtime:

* Without API credentials, deterministic stages still run and produce statistics plus a report skeleton.
* With `llm.enabled: true`, `inspect-cases` and `report` can call LLM-backed CaseInspector, HypothesisGenerator, and CriticAgent components.

Use:

* `litellm` for provider/model routing.
* `instructor` plus `pydantic` for structured outputs such as `claims.jsonl`.
* `openai` for OpenAI-compatible API clients.
