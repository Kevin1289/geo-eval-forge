DROP TABLE IF EXISTS t03_sensors;
DROP TABLE IF EXISTS t03_zones;
CREATE TABLE t03_zones (id int PRIMARY KEY, geom geometry(Polygon, 4326));
INSERT INTO t03_zones VALUES
  (1, ST_GeomFromText('POLYGON((36.80 -1.30, 36.82 -1.30, 36.82 -1.28, 36.80 -1.28, 36.80 -1.30))', 4326)),
  (2, ST_GeomFromText('POLYGON((36.82 -1.30, 36.84 -1.30, 36.84 -1.28, 36.82 -1.28, 36.82 -1.30))', 4326));
CREATE INDEX ON t03_zones USING gist (geom);

CREATE TABLE t03_sensors (id int PRIMARY KEY, geom geometry(Point, 4326));
INSERT INTO t03_sensors VALUES
  (1, ST_SetSRID(ST_MakePoint(36.81,  -1.29),  4326)),
  (2, ST_SetSRID(ST_MakePoint(36.83,  -1.29),  4326)),
  (3, ST_SetSRID(ST_MakePoint(36.85,  -1.29),  4326)),
  (4, ST_SetSRID(ST_MakePoint(36.815, -1.285), 4326));
CREATE INDEX ON t03_sensors USING gist (geom);
