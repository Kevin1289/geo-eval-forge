#!/usr/bin/env bash
# Publish the PostGIS `zones` table as a GeoServer layer (workspace geoeval).
# Run AFTER `make seed` has created the zones table. Idempotent-ish (ignores
# "already exists" errors from re-runs).
set -euo pipefail

GS="${GEOSERVER_URL:-http://geoserver:8080/geoserver}"
U="${GEOSERVER_ADMIN_USER:-admin}"
P="${GEOSERVER_ADMIN_PASSWORD:-geoserver}"
WS="geoeval"
DS="geoeval_pg"
AUTH=(-u "${U}:${P}" -H "Content-Type: application/xml")

echo "waiting for GeoServer at ${GS} ..."
until curl -sf -o /dev/null "${GS}/web/"; do sleep 3; done

echo "creating workspace ${WS}"
curl -s "${AUTH[@]}" -XPOST "${GS}/rest/workspaces" \
  -d "<workspace><name>${WS}</name></workspace>" || true

echo "creating PostGIS datastore ${DS}"
curl -s "${AUTH[@]}" -XPOST "${GS}/rest/workspaces/${WS}/datastores" -d "
<dataStore>
  <name>${DS}</name>
  <connectionParameters>
    <host>${POSTGRES_HOST:-postgis}</host>
    <port>${POSTGRES_PORT:-5432}</port>
    <database>${POSTGRES_DB:-geoeval}</database>
    <user>${POSTGRES_USER:-geoeval}</user>
    <passwd>${POSTGRES_PASSWORD:-geoeval}</passwd>
    <dbtype>postgis</dbtype>
  </connectionParameters>
</dataStore>" || true

echo "publishing layer ${WS}:zones"
curl -s "${AUTH[@]}" -XPOST "${GS}/rest/workspaces/${WS}/datastores/${DS}/featuretypes" -d "
<featureType><name>zones</name><srs>EPSG:4326</srs></featureType>" || true

echo "done: ${GS}/${WS}/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=${WS}:zones&resultType=hits"
