-- Correct: cast to geography so the 1000 is METRES and ST_Area returns m².
SELECT SUM(ST_Area(ST_Buffer(geom::geography, 1000.0)))::float AS value
FROM t02_points;
