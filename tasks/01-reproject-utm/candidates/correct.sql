-- Correct: ST_Transform actually reprojects the coordinates into EPSG:32737.
SELECT id, ST_AsGeoJSON(ST_Transform(geom, 32737)) AS geojson
FROM t01_points
ORDER BY id;
