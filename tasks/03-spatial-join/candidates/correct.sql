-- Correct: ST_Contains tests actual point-in-polygon; a LEFT JOIN keeps sensors
-- that fall in no zone, and COALESCE maps them to 0.
SELECT s.id AS id,
       COALESCE(z.id, 0) AS zone_id,
       ST_AsGeoJSON(s.geom) AS geojson
FROM t03_sensors s
LEFT JOIN t03_zones z ON ST_Contains(z.geom, s.geom)
ORDER BY s.id;
