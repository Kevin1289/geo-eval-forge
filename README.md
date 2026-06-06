# geo-eval-forge

**A reproducible GeoAI benchmark + eval harness for the open-source geospatial stack (QGIS / PyQGIS · GDAL/OGR · PostGIS · GeoServer).**

LLMs are good at *talking about* GIS and bad at *doing* it: they compute distances in degrees, confuse `ST_Intersects` with `ST_Intersection`, filter with `ST_Distance` instead of the index-aware `ST_DWithin`, blend QGIS 2/3/4 APIs, and — most dangerously — they answer **unsolvable** spatial questions instead of refusing them. Published benchmarks (GeoBenchX, GeoAnalystBench) put the best models around ~55% on real multi-step GIS work.

`geo-eval-forge` turns those failure modes into a **machine-graded benchmark**. Every task ships:

1. a natural-language prompt,
2. a **golden answer** computed by the real geo stack,
3. one or more **plausible-but-wrong "AI-rot" candidates**, and
4. a **deterministic verifier** that proves the golden passes and each wrong candidate fails *in its documented way* — by running PostGIS/GDAL, not by eyeballing.

The result is exactly the artifact an AI-training contract pays for: hard, verifiable, contrastive (correct vs. wrong) tasks with an automatic grader — plus a dashboard that lets a reviewer *see* the spatial error on a map.

> **Why this is hard to fake:** the dangerous GIS errors *execute cleanly and look right* — a buffer area in degrees returns a number, a wrong-CRS layer renders on top of the right one. So the grader can't trust "did it run"; it checks the **value/geometry against a golden answer within tolerance**, and for unsolvable tasks it checks whether the model **refused**.

---

## What's in the box

```
docker-compose ──▶ postgis        seeded, deterministic synthetic GIS data
               ├──▶ geoserver      publishes a PostGIS layer over WMS/WFS
               └──▶ worker         GDAL + psql + python + the geoeval harness

geoeval (Python)
  loader   ── validate every task against schema/task.schema.json
  runner   ── execute a candidate (sql / shell / recorded artifact) → canonical output
  verifiers── numeric · vector_equiv · sql_result · crs_check · service_check · rejection
  judge    ── optional LLM-as-judge (Vertex AI), calibrated vs human labels (agreement reported)
  score    ── aggregate → results/results.json (leaderboard · rejection acc · failure taxonomy)

dashboard (Next.js, static export)
  Leaderboard · MapExplorer (MapLibre) · FailureTaxonomy · JudgeAgreement
```

### The task categories (each embeds a documented AI failure mode)

| Task | Category | The trap it catches |
|------|----------|---------------------|
| `01-reproject-utm` | CRS | *assigning* a CRS (`-a_srs`) instead of *reprojecting* (`-t_srs`) — coordinates never move |
| `02-buffer-area-projected` | CRS / measurement | computing buffer **area in degrees** (EPSG:4326) instead of a projected/equal-area CRS |
| `03-spatial-join` | topology | wrong predicate / centroid-in-polygon / swapped `ST_Contains` args |
| `04-indexed-dwithin` | performance + correctness | `ST_Distance < d` (seq scan, geographic) vs index-aware `ST_DWithin` |
| `05-unsolvable-coverage` | **rejection** | silently computing a region-wide metric when the input only covers part of it |
| `06-service-wfs` | OGC services | publishing a PostGIS layer and reading it back correctly over WFS |

---

## Quickstart

**Offline (no Docker, no API key)** — the core grader + dashboard run on the recorded candidates:

```bash
# 1. run the harness against the bundled correct + wrong candidates
make run            # → results/results.json  (+ per-task GeoJSON for the map)

# 2. prove golden passes / wrong fails / schema valid
make test

# 3. view it
make dashboard      # next build/export → dashboard/out/  (open index.html)
```

**Live stack** — produce golden answers from the real engines and run service tasks:

```bash
make up             # boot postgis + geoserver + worker
make seed           # deterministic synthetic data → PostGIS + files
make run-live       # execute candidates against PostGIS/GeoServer, then verify
make down
```

**Live model baseline (optional, Vertex AI)** — measure a real model on the suite:

```bash
export GOOGLE_CLOUD_PROJECT=... GOOGLE_APPLICATION_CREDENTIALS=...
geoeval run --adapter vertex --model gemini-2.5-pro
geoeval judge --adapter vertex     # LLM-as-judge, then reports human-agreement
```

---

## How a task is defined

Every task is a directory validated against [`schema/task.schema.json`](schema/task.schema.json):

```
tasks/02-buffer-area-projected/
├── task.json            # prompt, category, solvable, inputs, expected, verifier+tolerance
├── golden/
│   ├── solution.sql     # the reference solution that PRODUCES the golden answer
│   └── answer.json      # the committed golden value (total area in m², with tolerance)
└── candidates/
    ├── correct.sql      # buffers in a projected CRS → passes
    └── wrong_degrees.sql# buffers in EPSG:4326 → grossly wrong number → fails
```

The harness loads the task, runs each candidate, and the `numeric` verifier checks the
result against `golden/answer.json` within the task's tolerance. The wrong candidate's
failure (and *why*) is recorded as the supervised signal.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full task-authoring guide.

---

## Design principles

- **Proven, not asserted.** Golden answers come from real engines; verifiers re-check them. CI fails if a golden stops passing or a wrong candidate starts passing.
- **Offline-first.** The whole pipeline + dashboard run with zero API key via recorded candidates. The Vertex AI adapter is only for *live* model baselines.
- **Deterministic.** Synthetic data is generated with fixed seeds; verifiers are tolerance-based; runs are reproducible.
- **Honest judging.** The optional LLM-as-judge reports its measured agreement with a small hand-annotated set rather than assuming it.
- **Rejection is a first-class metric.** The hardest GIS-AI gap is knowing when a task *can't* be answered; the unsolvable subset measures exactly that.

## Status & roadmap

This is milestone 1 — a runnable vertical slice (6 tasks, deterministic core, dashboard). Next:
- Scale to the full ~30-task suite (same pattern).
- Add the **PyQGIS Processing** category (headless `qgis_process`, version-pinned 3.x/4.x).
- Wire live Vertex baselines + expand judge calibration.
- Add raster tasks (`raster_stats` verifier).

## Security & credentials

The credentials in `docker-compose.yml` / `.env.example` (`geoeval` / `geoserver`) are
**insecure defaults for local development only** — override them via a `.env` file and
don't expose ports 5432/8080 publicly. No secrets are committed; LLM adapters read
credentials from the environment at runtime. The live runner executes each task's
solution files against the local stack, so only run task candidates you trust. See
[SECURITY.md](SECURITY.md).

## License

Code: [MIT](LICENSE). Benchmark data (`tasks/`, `data/`, `judge/`): [CC BY 4.0](LICENSE-DATA).
