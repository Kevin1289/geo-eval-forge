DROP TABLE IF EXISTS t01_points;
CREATE TABLE t01_points (id int PRIMARY KEY, geom geometry(Point, 4326));
INSERT INTO t01_points VALUES
  (1, ST_SetSRID(ST_MakePoint(36.81, -1.29), 4326)),
  (2, ST_SetSRID(ST_MakePoint(36.83, -1.31), 4326)),
  (3, ST_SetSRID(ST_MakePoint(36.79, -1.27), 4326));
