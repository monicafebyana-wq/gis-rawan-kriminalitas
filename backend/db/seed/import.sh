#!/bin/sh
# Impor data bersih ke database. Dijalankan DI DALAM container:
#   docker exec gis_kriminalitas_db sh /seed/import.sh          (total diharapkan default 1163)
#   docker exec gis_kriminalitas_db sh /seed/import.sh 1200     (kalau datanya memang berbeda)
# Prasyarat: migrasi 001-003 sudah dijalankan (sh /migrations/run.sh).
exec psql -v ON_ERROR_STOP=1 -v expect_total="${1:-1163}" \
     -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-gis_kriminalitas}" \
     -f "$(dirname "$0")/import_kasus.sql"
