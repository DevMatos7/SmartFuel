"""Etapa B — homologação 7 dias (03/07/2026 a 09/07/2026)."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx

BASE = os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")
EMAIL = os.environ.get("HOMOLOG_EMAIL", "admin@test.com")
PASSWORD = os.environ.get("HOMOLOG_PASSWORD", "SenhaSegura123")
STATION_ID = os.environ.get("HOMOLOG_STATION_ID", "1edc5c8b-0ba1-405c-a000-03e61e31521e")
DATE_FROM = date.fromisoformat(os.environ.get("HOMOLOG_DATE_FROM", "2026-07-03"))
DATE_TO = date.fromisoformat(os.environ.get("HOMOLOG_DATE_TO", "2026-07-09"))
POLL_SECONDS = int(os.environ.get("HOMOLOG_POLL_SECONDS", "1200"))
REPORT_PATH = Path(os.environ.get("HOMOLOG_REPORT_PATH", "docs/sprints/sprint-06-homologacao-etapa-b.md"))


def login(client: httpx.Client) -> dict[str, str]:
    token = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def wait_run(client: httpx.Client, headers: dict[str, str], run_id: str) -> dict:
    deadline = time.time() + POLL_SECONDS
    run: dict = {}
    while time.time() < deadline:
        run = client.get(f"/integrations/xpert/sync-runs/{run_id}", headers=headers).json()
        print(f"  {run['status']} read={run.get('rows_read')} applied={run.get('rows_applied')} unchanged={run.get('rows_unchanged')}")
        if run["status"] not in ("QUEUED", "CONNECTING", "EXTRACTING", "STAGING", "VALIDATING", "APPLYING"):
            return run
        time.sleep(5)
    return run


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=180.0)
    headers = login(client)
    me = client.get("/auth/me", headers=headers).json()
    sources = client.get("/integrations/xpert/sources", headers=headers).json()
    source = sources[0]

    history_end = DATE_TO + timedelta(days=1)
    started = time.time()
    sync = client.post(
        "/integrations/xpert/sync-runs",
        headers=headers,
        json={
            "source_id": source["id"],
            "dataset_codes": ["FUEL_SALES_ITEMS"],
            "station_ids": [STATION_ID],
            "sync_mode": "INCREMENTAL_TIMESTAMP",
            "unsafe_homologation_acknowledged": True,
            "history_start_date": DATE_FROM.isoformat(),
            "history_end_date": history_end.isoformat(),
        },
    )
    sync.raise_for_status()
    run = wait_run(client, headers, sync.json()["runs"][0]["id"])
    elapsed = int(time.time() - started)

    params = {"date_from": DATE_FROM.isoformat(), "date_to": DATE_TO.isoformat()}
    summary = client.get("/analytics/fuel-sales/summary", headers=headers, params=params).json()
    quality = client.get("/analytics/fuel-sales/data-quality", headers=headers, params=params).json()
    trend = client.get("/analytics/fuel-sales/trend", headers=headers, params=params).json()

    report = f"""# SPRINT 6 — HOMOLOGAÇÃO REAL, ETAPA B — 7 DIAS

Gerado em: {time.strftime('%Y-%m-%d %H:%M:%S')}

## 1. Período e ambiente
- Período: `{DATE_FROM}` a `{DATE_TO}` (inclusivo)
- Posto: Matriz (`{STATION_ID}`)
- erp_branch_id: `2443`
- Fonte: UNSAFE (`sa`)
- Execução: manual ADMIN (`{me.get('email')}`)
- Agenda: bloqueada

## 2. Decisão DBA sobre CFOP 5.667
- **Pendente** — tratado como `PENDING_REVIEW` → `PENDING_CFOP_CLASSIFICATION`

## 3. Política CFOP
| CFOP | Tratamento |
|------|------------|
| 5.656 | INCLUDE_AS_SALE |
| 5.667 | PENDING_REVIEW |

## 4. Sync 7 dias
| Campo | Valor |
|-------|-------|
| Status | {run.get('status')} |
| Lidos | {run.get('rows_read')} |
| Aplicados | {run.get('rows_applied')} |
| Inalterados | {run.get('rows_unchanged')} |
| Erros | {run.get('rows_error')} |
| Duração | {elapsed}s |

## 5. Analytics consolidado
```json
{json.dumps(summary, ensure_ascii=False, indent=2)}
```

## 6. Qualidade
```json
{json.dumps(quality, ensure_ascii=False, indent=2)}
```

## 7. Tendência diária
```json
{json.dumps(trend, ensure_ascii=False, indent=2)}
```

## 8. Pendências
- CFOP 5.667 aguarda DBA
- Mapeamento VALOR1–4 provisório
- Incremental não homologado
- 30 dias bloqueados
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"Relatório: {REPORT_PATH}")
    return 0 if run.get("status") in ("COMPLETED", "PARTIAL") else 1


if __name__ == "__main__":
    sys.exit(main())
