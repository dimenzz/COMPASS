# Logging Guidelines

> How logging is done in this project.

---

## Overview

- CLI commands use `compass.cli.progress.CliProgress` for human-readable progress.
- Each stage command should print `START`, `DONE`, or `FAILED`, elapsed time, and the run-local log path.
- Durable stage logs live under `runs/{run_name}/logs/{stage}.log`; state metadata lives under `runs/{run_name}/state/{stage}.done.json`.
- External tool stdout/stderr should be redirected into a tool-specific run log such as `logs/search.mmseqs.log`, not streamed directly to the terminal.

---

## Log Levels

- Terminal output is concise progress only.
- Stage logs record input paths, output paths, count summaries, and selected parameters.
- Tool logs record the exact command and raw stdout/stderr.

---

## Structured Logging

- Stage state JSON should remain machine-readable and include start/finish timestamps plus a parameter hash.
- TSV/JSONL artifacts are the source of truth for biological/statistical outputs; logs are operational diagnostics.

---

## What to Log

- Stage start and completion in the CLI.
- Runtime duration in the CLI.
- Run directory and log path in the CLI.
- Input artifact paths, output artifact paths, row counts, and grouping/enrichment counts in stage logs.
- Exact external command lines and tool stdout/stderr in tool logs.

---

## What NOT to Log

- API keys or other credentials.
- Full LLM prompts containing unpublished hypotheses unless the user explicitly opts into prompt trace logging.
- Raw large biological sequences in routine stage logs; write them to explicit artifacts instead.
