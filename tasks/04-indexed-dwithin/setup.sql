DROP TABLE IF EXISTS t04_sensors;
CREATE TABLE t04_sensors (id int PRIMARY KEY, geom geometry(Point, 4326));
INSERT INTO t04_sensors VALUES
  (1, ST_SetSRID(ST_MakePoint(36.811, -1.29),  4326)),  -- ~111 m  -> IN
  (2, ST_SetSRID(ST_MakePoint(36.815, -1.29),  4326)),  -- ~556 m  -> OUT
  (3, ST_SetSRID(ST_MakePoint(36.81,  -1.293), 4326)),  -- ~334 m  -> IN
  (4, ST_SetSRID(ST_MakePoint(36.83,  -1.29),  4326));  -- ~2.2 km -> OUT
CREATE INDEX ON t04_sensors USING gist (geom);
ANALYZE t04_sensors;
