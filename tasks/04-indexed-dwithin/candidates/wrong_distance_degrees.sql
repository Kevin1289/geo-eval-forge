-- BUG: ST_Distance on geometry in EPSG:4326 returns DEGREES, so "< 500" means
-- "within 500 degrees" — i.e. everything on Earth. It also cannot use the GiST
-- index (a function on the column forces a sequential scan). Returns all 4 ids.
SELECT s.id AS id
FROM t04_sensors s
WHERE ST_Distance(s.geom, ST_SetSRID(ST_MakePoint(36.81, -1.29), 4326)) < 500
ORDER BY s.id;
