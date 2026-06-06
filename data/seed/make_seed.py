"""Deterministic synthetic GIS data for the benchmark.

Generates two layers in EPSG:4326 around Nairobi (UTM zone 37S → EPSG:32737 —
deliberately Southern-Hemisphere to counter the Northern bias of most GIS demos):

- ``zones``   : a 2×2 grid of square polygons covering PART of the study area
                (so a region-wide question over it is genuinely unsolvable).
- ``sensors`` : points, some inside zones and some outside.

Always writes canonical GeoJSON to ``data/seed/out/``. If a PostGIS connection is
reachable (and psycopg is installed) it also loads the layers with GiST indexes.
Determinism comes from a fixed RNG seed — no wall-clock, no unseeded randomness.
"""
from __future__ import annotations

import json
import os
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"

# Study area (Nairobi). UTM zone 37S = EPSG:32737.
LON0, LAT0 = 36.80, -1.30
CELL = 0.02          # ~2.2 km cells
GRID = 2             # 2×2 = 4 zones (covering the SW quadrant of the wider area)
N_SENSORS = 40
SEED = 42
UTM_EPSG = 32737


def _square(i: int, j: int) -> list[list[float]]:
    x0, y0 = LON0 + i * CELL, LAT0 + j * CELL
    x1, y1 = x0 + CELL, y0 + CELL
    return [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]


def build_zones() -> dict:
    feats = []
    zid = 1
    for j in range(GRID):
        for i in range(GRID):
            feats.append({
                "type": "Feature",
                "properties": {"id": zid, "name": f"zone-{zid}"},
                "geometry": {"type": "Polygon", "coordinates": _square(i, j)},
            })
            zid += 1
    return {"type": "FeatureCollection", "crs_epsg": 4326, "features": feats}


def build_sensors() -> dict:
    rng = random.Random(SEED)
    # study area spans a 4×4 grid of cells, but zones only cover the 2×2 SW corner
    span = GRID * 2 * CELL
    feats = []
    for sid in range(1, N_SENSORS + 1):
        lon = LON0 + rng.random() * span
        lat = LAT0 + rng.random() * span
        feats.append({
            "type": "Feature",
            "properties": {"id": sid},
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
        })
    return {"type": "FeatureCollection", "crs_epsg": 4326, "features": feats}


def write_files(layers: dict[str, dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fc in layers.items():
        (OUT / f"{name}.geojson").write_text(json.dumps(fc, indent=2))
        print(f"  wrote {OUT / (name + '.geojson')}  ({len(fc['features'])} features)")


def load_postgis(layers: dict[str, dict]) -> bool:
    try:
        import psycopg
    except Exception:
        print("  (psycopg not installed — skipping PostGIS load)")
        return False

    dsn = (
        f"host={os.environ.get('POSTGRES_HOST', 'postgis')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ.get('POSTGRES_DB', 'geoeval')} "
        f"user={os.environ.get('POSTGRES_USER', 'geoeval')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', 'geoeval')}"
    )
    try:
        conn = psycopg.connect(dsn, connect_timeout=4)
    except Exception as exc:
        print(f"  (PostGIS not reachable — skipping load: {exc})")
        return False

    with conn, conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        cur.execute("DROP TABLE IF EXISTS sensors; DROP TABLE IF EXISTS zones;")
        cur.execute("CREATE TABLE zones (id int primary key, name text, geom geometry(Polygon,4326));")
        cur.execute("CREATE TABLE sensors (id int primary key, geom geometry(Point,4326));")
        for f in layers["zones"]["features"]:
            cur.execute(
                "INSERT INTO zones (id, name, geom) VALUES (%s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s),4326));",
                (f["properties"]["id"], f["properties"]["name"], json.dumps(f["geometry"])),
            )
        for f in layers["sensors"]["features"]:
            cur.execute(
                "INSERT INTO sensors (id, geom) VALUES (%s, ST_SetSRID(ST_GeomFromGeoJSON(%s),4326));",
                (f["properties"]["id"], json.dumps(f["geometry"])),
            )
        cur.execute("CREATE INDEX ON zones USING gist (geom);")
        cur.execute("CREATE INDEX ON sensors USING gist (geom);")
        cur.execute("ANALYZE zones; ANALYZE sensors;")
    print("  loaded PostGIS tables zones, sensors (GiST + ANALYZE)")
    return True


def main() -> None:
    print(f"seeding study area @ ({LON0},{LAT0}) — UTM EPSG:{UTM_EPSG}")
    layers = {"zones": build_zones(), "sensors": build_sensors()}
    write_files(layers)
    load_postgis(layers)


if __name__ == "__main__":
    main()
