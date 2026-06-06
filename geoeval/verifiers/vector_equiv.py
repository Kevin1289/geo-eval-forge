"""Grade a vector output (canonical GeoJSON FeatureCollection) for geometric and
attribute equivalence to the golden answer.

Canonical artifact format (see CONTRIBUTING.md)::

    { "type": "FeatureCollection", "crs_epsg": 32633, "features": [...] }

``crs_epsg`` is the EPSG of the coordinates *as written*. We compare it first:
a layer whose CRS was *relabeled* but not *reprojected* (the classic GDAL
``-a_srs`` vs ``-t_srs`` trap) will fail here even though it "loads fine".
"""
from __future__ import annotations

from typing import Any

from ..models import Task, Verdict

try:  # shapely is GEOS-backed and gives us real geometric equality
    from shapely.geometry import shape
    _HAVE_SHAPELY = True
except Exception:  # pragma: no cover - exercised only in minimal envs
    _HAVE_SHAPELY = False


def _index(fc: dict, id_field: str) -> dict:
    out = {}
    for feat in fc.get("features", []):
        fid = feat.get("properties", {}).get(id_field)
        out[fid] = feat
    return out


def verify(task: Task, produced: Any, params: dict) -> Verdict:
    if not _HAVE_SHAPELY:
        return Verdict(False, 0.0, "shapely not available to compare geometries", None, None)
    if not isinstance(produced, dict) or produced.get("type") != "FeatureCollection":
        return Verdict(False, 0.0, "candidate output is not a FeatureCollection", None, produced)

    gold = task.golden or {}
    tol = float(params.get("tolerance", 0.0))            # metres, in the layer CRS
    id_field = params.get("id_field", "id")
    check_attrs = params.get("check_attrs")

    g_crs, p_crs = gold.get("crs_epsg"), produced.get("crs_epsg")
    if g_crs != p_crs:
        return Verdict(
            False, 0.0,
            f"CRS mismatch: candidate EPSG:{p_crs} vs golden EPSG:{g_crs} "
            f"(coordinates were not reprojected to the target CRS)",
            f"EPSG:{g_crs}", f"EPSG:{p_crs}",
        )

    gi, pi = _index(gold, id_field), _index(produced, id_field)
    if set(gi) != set(pi):
        missing, extra = set(gi) - set(pi), set(pi) - set(gi)
        return Verdict(False, 0.0,
                       f"feature id set differs (missing={sorted(missing)[:5]}, extra={sorted(extra)[:5]})",
                       len(gi), len(pi))

    mismatches: list[str] = []
    for fid, gf in gi.items():
        pf = pi[fid]
        gg, pg = shape(gf["geometry"]), shape(pf["geometry"])
        if not (gg.equals(pg) or gg.hausdorff_distance(pg) <= tol):
            mismatches.append(f"{fid}:geometry(hd={gg.hausdorff_distance(pg):.4g})")
            continue
        if check_attrs:
            attrs = check_attrs if isinstance(check_attrs, list) else [
                k for k in gf.get("properties", {}) if k != id_field
            ]
            for a in attrs:
                if gf["properties"].get(a) != pf["properties"].get(a):
                    mismatches.append(f"{fid}:attr[{a}]")

    n = max(1, len(gi))
    if not mismatches:
        return Verdict(True, 1.0, f"all {len(gi)} features match within {tol} m", len(gi), len(pi))
    return Verdict(False, max(0.0, 1 - len(mismatches) / n),
                   f"{len(mismatches)} mismatch(es): {mismatches[:6]}", len(gi), len(pi))
