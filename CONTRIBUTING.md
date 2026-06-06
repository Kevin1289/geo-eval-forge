# Contributing — authoring a benchmark task

A task is a directory under `tasks/` that the harness can grade automatically. The
goal of every task is to capture a **documented way LLMs get GIS wrong**, with a
golden answer and at least one plausible-but-wrong candidate.

## 1. Anatomy of a task

```
tasks/<NN-slug>/
├── task.json            # the contract (validated against schema/task.schema.json)
├── golden/
│   ├── solution.<ext>   # the reference solution that produces the answer (sql/sh/py)
│   └── answer.json      # the committed golden answer (a canonical artifact or value)
└── candidates/
    ├── correct.<ext>    # a known-correct candidate (must PASS)
    └── wrong_<why>.<ext># one or more plausible-wrong candidates (must FAIL)
```

## 2. `task.json` fields

| field | meaning |
|-------|---------|
| `id` | unique slug, matches the directory name |
| `title` | short human title |
| `category` | one of `crs`, `topology`, `performance`, `services`, `rejection`, `measurement` |
| `difficulty` | `easy` \| `medium` \| `hard` |
| `prompt` | the natural-language task a model would be given |
| `solvable` | `true` for normal tasks; `false` for rejection tasks |
| `rejection_reason` | (unsolvable only) why the task cannot be answered |
| `inputs` | named layers/files the task uses (seeded by `make seed`) |
| `expected` | descriptor of the golden answer (`kind` + a reference path/value) |
| `verifier` | `{ "name": ..., "params": {...}, "tolerance": ... }` |

## 3. The canonical artifact format

So verifiers can run **without GDAL** (and stay unit-testable), vector outputs are
stored as **GeoJSON with an explicit CRS**:

```json
{ "type": "FeatureCollection",
  "crs_epsg": 32633,
  "features": [ { "type": "Feature", "properties": {"id": 1}, "geometry": {...} } ] }
```

- `crs_epsg` is the EPSG of the **coordinates as written** (not assumed WGS84).
- The live runner normalizes PostGIS/GDAL output into this form before verifying;
  offline candidates are already in this form.

Scalar answers are `{"value": <number>, "unit": "..."}`.

## 4. Verifiers

| verifier | grades | passes when |
|----------|--------|-------------|
| `numeric` | a scalar | `|got - golden| <= tolerance` (abs or relative) |
| `vector_equiv` | a FeatureCollection | same features, geometry equal within `tolerance` m, attributes match |
| `sql_result` | a result set | same rows (order-insensitive unless `ordered: true`) |
| `crs_check` | a FeatureCollection's `crs_epsg` | equals `expected.epsg` |
| `service_check` | a GeoServer WFS/WMS response | feature count / non-blank tile matches |
| `rejection` | a candidate's refusal | unsolvable→refused (pass), solvable→attempted (pass) |

A candidate may be a recorded artifact (offline) or a command the runner executes
against the live stack. Mark which via the candidate file extension:
`.json` = recorded artifact, `.sql` = PostGIS, `.sh` = shell (GDAL), `.txt` = a
rejection statement.

## 5. Checklist before you open a PR

1. `make validate` — `task.json` matches the schema.
2. `make run && make test` — your `correct` candidate **passes**, every `wrong_*`
   **fails**, and the failure detail explains *why*.
3. Add a one-line entry to the task table in `README.md`.
4. Keep data small and synthetic (or CC-licensed). Determinism matters: no
   wall-clock / RNG without a fixed seed.
