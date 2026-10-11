#!/bin/sh
# Runner migrasi sederhana. Dijalankan DI DALAM container database:
#   docker exec gis_kriminalitas_db sh /migrations/run.sh
# - Menerapkan file [0-9]*.sql berurutan, masing-masing dalam 1 transaksi.
# - Yang sudah pernah diterapkan dilewati (dicatat di tabel schema_migrations).
# - Berhenti di error pertama.
set -e
PSQL="psql -v ON_ERROR_STOP=1 -q -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-gis_kriminalitas}"
DIR="$(dirname "$0")"

$PSQL -c "CREATE TABLE IF NOT EXISTS schema_migrations (nama TEXT PRIMARY KEY, diterapkan_pada TIMESTAMPTZ NOT NULL DEFAULT now())"

for f in "$DIR"/[0-9]*.sql; do
  n="$(basename "$f")"
  sudah="$($PSQL -tA -c "SELECT 1 FROM schema_migrations WHERE nama = '$n'")"
  if [ "$sudah" = "1" ]; then
    echo "lewati    $n"
    continue
  fi
  echo "terapkan  $n"
  $PSQL --single-transaction -f "$f"
  $PSQL -c "INSERT INTO schema_migrations (nama) VALUES ('$n')"
done
echo "Selesai."
