# Database Guidelines

> Database patterns and conventions for this project.

---

## Overview

<!--
Document your project's database conventions here.

Questions to answer:
- What ORM/query library do you use?
- How are migrations managed?
- What are the naming conventions for tables/columns?
- How do you handle transactions?
-->

(To be filled by the team)

---

## Query Patterns

- Expensive cross-family background counts must be precomputed as reusable artifacts rather than recomputed inside run stages.
- `enrich` must read `database.family30_background` (`family30_id`, `num_90_representatives`) and should not issue full `clusters.db` scans during each run.
- SQLite repository calls inside run stages should be batched when filtering by IDs and should be avoided for whole-database aggregation unless the command is explicitly building a cache.

---

## Migrations

<!-- How to create and run migrations -->

(To be filled by the team)

---

## Naming Conventions

<!-- Table names, column names, index names -->

(To be filled by the team)

---

## Common Mistakes

- Recomputing the 30% family background inside `enrich` makes each run scale with the whole cluster database instead of the observed context table.
