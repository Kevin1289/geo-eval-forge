-- BUG (the #1 silent GIS failure): the layer is EPSG:4326, so this buffers by
-- ~0.009 DEGREES (a naive "1 km ≈ 0.009°" conversion) and ST_Area then returns
-- SQUARE DEGREES, not square metres. The query runs fine and returns a tiny
-- number ~7.6e-4 instead of ~9.4e6.
SELECT SUM(ST_Area(ST_Buffer(geom, 0.009)))::float AS value
FROM t02_points;
