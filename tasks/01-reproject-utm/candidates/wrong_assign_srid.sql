-- BUG (the classic -a_srs vs -t_srs / "define vs reproject" trap):
-- ST_SetSRID only RELABELS the CRS metadata to 32737; the coordinates are still
-- lon/lat degrees. The layer now CLAIMS to be UTM but never moved — it lines up
-- with nothing. crs_check passes (label is right) but vector_equiv fails.
SELECT id, ST_AsGeoJSON(ST_SetSRID(geom, 32737)) AS geojson
FROM t01_points
ORDER BY id;
