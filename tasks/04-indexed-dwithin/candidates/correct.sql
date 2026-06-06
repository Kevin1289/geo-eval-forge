-- Correct: ST_DWithin on geography measures METRES and is index-aware (the GiST
-- index on geom is used via the spheroid bbox). Returns sensors 1 and 3.
SELECT s.id AS id
FROM t04_sensors s
WHERE ST_DWithin(s.geom::geography,
                 ST_SetSRID(ST_MakePoint(36.81, -1.29), 4326)::geography,
                 500)
ORDER BY s.id;
