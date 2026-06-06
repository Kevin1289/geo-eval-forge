-- BUG: uses the NEAREST zone (<-> distance operator) instead of the CONTAINING
-- zone. Every sensor gets a zone — including sensor 3, which is outside every
-- polygon and should be 0. Geometry matches the golden; the zone_id attribute
-- is wrong, so vector_equiv (check_attrs: zone_id) catches it.
SELECT s.id AS id,
       (SELECT z.id FROM t03_zones z ORDER BY z.geom <-> s.geom LIMIT 1) AS zone_id,
       ST_AsGeoJSON(s.geom) AS geojson
FROM t03_sensors s
ORDER BY s.id;
