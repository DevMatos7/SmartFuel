"""Análise da run SUPPLIERS anterior via PostgreSQL."""

from __future__ import annotations

import json
import os

import psycopg

RUN_ID = os.environ.get("RUN_ID", "225a483e-18b4-4d30-b64b-6898734ee188")
DSN = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://smartfuel:smartfuel@postgres:5432/smartfuel",
)


def main() -> None:
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status, rows_read, rows_applied, rows_quarantined, rows_inserted,
                       rows_updated, rows_unchanged, rows_error, checkpoint_before, checkpoint_after,
                       started_at, finished_at, error_code
                FROM erp_sync_runs WHERE id = %s
                """,
                (RUN_ID,),
            )
            print("RUN", cur.fetchone())

            cur.execute(
                """
                SELECT error_code, COUNT(*) FROM erp_sync_errors
                WHERE sync_run_id = %s GROUP BY error_code ORDER BY COUNT(*) DESC
                """,
                (RUN_ID,),
            )
            print("ERRORS_BY_CODE", cur.fetchall())

            cur.execute(
                """
                SELECT processing_status, COUNT(*) FROM erp_staging_records
                WHERE sync_run_id = %s GROUP BY processing_status
                """,
                (RUN_ID,),
            )
            print("STAGING_BY_STATUS", cur.fetchall())

            cur.execute(
                """
                SELECT normalized_payload->>'source_cnpj_raw' AS raw,
                       normalized_payload->>'erp_cnpj' AS cnpj,
                       normalized_payload->>'erp_cpf' AS cpf,
                       COUNT(*)
                FROM erp_staging_records
                WHERE sync_run_id = %s AND processing_status = 'QUARANTINED'
                GROUP BY 1,2,3 ORDER BY COUNT(*) DESC LIMIT 10
                """,
                (RUN_ID,),
            )
            print("QUARANTINED_SAMPLES", cur.fetchall())

            cur.execute(
                """
                SELECT raw_payload->>'source_cnpj' AS raw_cnpj, COUNT(*)
                FROM erp_staging_records
                WHERE sync_run_id = %s AND processing_status = 'QUARANTINED'
                GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 15
                """,
                (RUN_ID,),
            )
            print("QUARANTINED_RAW_CNPJ", cur.fetchall())

            cur.execute(
                """
                SELECT mapping_status, COUNT(*)
                FROM erp_suppliers
                WHERE last_sync_run_id = %s
                GROUP BY mapping_status
                """,
                (RUN_ID,),
            )
            print("SUPPLIERS_BY_MAPPING", cur.fetchall())

            cur.execute(
                """
                SELECT COUNT(*) FROM erp_suppliers
                WHERE station_id = '1edc5c8b-0ba1-405c-a000-03e61e31521e'
                """,
            )
            print("TOTAL_SUPPLIERS", cur.fetchone())


if __name__ == "__main__":
    main()
