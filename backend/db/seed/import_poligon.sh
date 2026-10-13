#!/bin/sh
# Impor poligon wilayah ke kolom polsek.geom + validasi geometri. Dijalankan DI DALAM container:
#   docker exec gis_kriminalitas_db sh /seed/import_poligon.sh                    (default: polsek_poligon.geojson)
#   docker exec gis_kriminalitas_db sh /seed/import_poligon.sh polsek_baru.geojson (berkas lain di data/geojson/)
# Prasyarat: sh /seed/import.sh sudah dijalankan (tabel polsek terisi).
BERKAS="/data/geojson/${1:-polsek_poligon.geojson}"
if [ ! -s "$BERKAS" ]; then
  echo "ERROR: berkas tidak ditemukan atau kosong: $BERKAS"
  echo "Isi folder data/geojson di container: $(ls /data/geojson 2>/dev/null | tr '\n' ' ')"
  echo "(Kalau baru menambah berkas: pastikan 'docker compose up -d' sudah dijalankan agar folder ter-mount.)"
  exit 1
fi
exec psql -v ON_ERROR_STOP=1 -v berkas="$BERKAS" \
     -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-gis_kriminalitas}" \
     -f "$(dirname "$0")/import_poligon.sql"
