-- Runs once on first PostGIS container start (docker-entrypoint-initdb.d).
CREATE EXTENSION IF NOT EXISTS postgis;
