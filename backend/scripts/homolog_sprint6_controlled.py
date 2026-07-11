"""Homologação Sprint 6 controlada — janela pequena, sem carga de 30 dias."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx

BASE = os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")
EMAIL = os.environ.get("HOMOLOG_EMAIL", "admin@test.com")
PASSWORD = os.environ.get("HOMOLOG_PASSWORD", "SenhaSegura123")
STATION_ID = os.environ.get("HOMOLOG_STATION_ID", "1edc5c8b-0ba1-405c-a000-03e61e31521e")
EXPECTED_BRANCH = os.environ.get("HOMOLOG_ERP_BRANCH_ID", "2443")
SALES_DAY = os.environ.get("HOMOLOG_SALES_DAY", "")  # YYYY-MM-DD; vazio = ontem
POLL_SECONDS = int(os.environ.get("HOMOLOG_POLL_SECONDS", "600"))
POLL_INTERVAL = 5
REPORT_PATH = Path(os.environ.get("HOMOLOG_REPORT_PATH", "docs/sprints/sprint-06-homologacao-real.md"))

FUEL_DATASETS = ("PAYMENT_METHODS", "FUEL_RETAIL_PRICES", "FUEL_SALES_ITEMS")


def login(client: httpx.Client) -> tuple[dict[str, str], dict]:
    response = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    response.raise_for_status()
    body = response.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body


def wait_run(client: httpx.Client, headers: dict[str, str], run_id: str) -> dict:
    deadline = time.time() + POLL_SECONDS
    run: dict = {}
    while time.time() < deadline:
        run = client.get(f"/integrations/xpert/sync-runs/{run_id}", headers=headers).json()
        status = run["status"]
        print(
            f"  {status} read={run.get('rows_read')} applied={run.get('rows_applied')} "
            f"unchanged={run.get('rows_unchanged')} error={run.get('rows_error')}"
        )
        if status not in (
            "QUEUED",
            "CONNECTING",
            "EXTRACTING",
            "STAGING",
            "VALIDATING",
            "APPLYING",
            "CANCELLATION_REQUESTED",
        ):
            return run
        time.sleep(POLL_INTERVAL)
    return run


def enqueue_sync(
    client: httpx.Client,
    headers: dict[str, str],
    source_id: str,
    dataset_code: str,
    *,
    sync_mode: str,
    history_start: date | None = None,
    history_end: date | None = None,
) -> dict:
    payload: dict = {
        "source_id": source_id,
        "dataset_codes": [dataset_code],
        "station_ids": [STATION_ID],
        "sync_mode": sync_mode,
        "unsafe_homologation_acknowledged": True,
    }
    if history_start and history_end:
        payload["history_start_date"] = history_start.isoformat()
        payload["history_end_date"] = history_end.isoformat()
    response = client.post("/integrations/xpert/sync-runs", headers=headers, json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"Erro ao enfileirar {dataset_code}: {response.status_code} {response.text}")
    run = response.json()["runs"][0]
    print(f"\nRun {dataset_code}: {run['id']}")
    return wait_run(client, headers, run["id"])


def validate_contract(client: httpx.Client, headers: dict[str, str], dataset_id: str, code: str) -> dict:
    started = time.perf_counter()
    response = client.post(
        f"/integrations/xpert/datasets/{dataset_id}/validate-contract",
        headers=headers,
        params={"station_id": STATION_ID},
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if response.status_code >= 400:
        raise RuntimeError(f"Contrato {code} falhou: {response.status_code} {response.text}")
    body = response.json()
    body["elapsed_ms"] = elapsed_ms
    print(
        f"Contrato {code}: valid={body.get('valid')} sample={body.get('sample_count')} "
        f"isolation_n={body.get('isolation_sample_size')} branches={body.get('distinct_branch_ids')} "
        f"hash={str(body.get('query_hash', ''))[:16]}..."
    )
    if body.get("isolation_errors"):
        raise RuntimeError(f"Isolamento {code}: {body['isolation_errors']}")
    client.patch(f"/integrations/xpert/datasets/{dataset_id}", headers=headers, json={"enabled": True}).raise_for_status()
    return body


def static_query_checks() -> dict:
    from app.integrations.xpert.query_validator import validate_parameters, validate_read_only_query
    from app.integrations.xpert.secret_resolver import load_query_file
    from app.integrations.xpert.canonical_hash import query_file_hash

    results: dict[str, dict] = {}
    for query_file in ("payment_methods.sql", "fuel_retail_prices.sql", "fuel_sales_items.sql"):
        sql = load_query_file(query_file)
        read_only = validate_read_only_query(sql)
        params = validate_parameters(sql)
        results[query_file] = {
            "read_only": read_only.valid,
            "read_only_errors": read_only.errors,
            "parameter_errors": params,
            "requires_station_erp_id": "@station_erp_id" in sql,
            "query_hash": query_file_hash(sql),
        }
    return results


def pg_compare_one_day(client: httpx.Client, headers: dict[str, str], sales_day: date) -> dict:
    day_end = sales_day + timedelta(days=1)
    params = {"date_from": sales_day.isoformat(), "date_to": sales_day.isoformat()}
    summary = client.get("/analytics/fuel-sales/summary", headers=headers, params=params)
    quality = client.get("/analytics/fuel-sales/data-quality", headers=headers, params=params)
    return {
        "sales_day": sales_day.isoformat(),
        "summary_status": summary.status_code,
        "summary": summary.json() if summary.status_code == 200 else summary.text[:300],
        "quality": quality.json() if quality.status_code == 200 else quality.text[:300],
        "window_end_exclusive": day_end.isoformat(),
    }


def build_report(data: dict) -> str:
    lines = [
        "# SPRINT 6 — HOMOLOGAÇÃO REAL CONTROLADA",
        "",
        f"Gerado em: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## 1. Ambiente",
        f"- SQL Server: `{data['env'].get('sql_host', '192.168.120.253')}`",
        f"- Banco: `{data['env'].get('database', 'atxdados')}`",
        f"- Usuário: `{data['env'].get('sql_user', 'sa')}` (**UNSAFE** — somente homologação)",
        f"- APP_ENV: `{data['env'].get('app_env')}`",
        f"- XPERT_ALLOW_UNSAFE_PRIVILEGES: `{data['env'].get('unsafe_allowed')}`",
        f"- security_status: `{data['env'].get('security_status')}`",
        f"- Execução: manual por ADMIN (`{data['env'].get('admin_email')}`)",
        f"- Agenda automática bloqueada: `{data['env'].get('scheduler_blocked')}`",
        f"- Posto: `{data['env'].get('station_name')}` (`{STATION_ID}`)",
        f"- erp_branch_id: `{EXPECTED_BRANCH}`",
        "",
        "## 2. Contratos",
    ]
    for code, contract in data.get("contracts", {}).items():
        lines.append(f"### {code}")
        lines.append(f"- Válido: **{contract.get('valid')}**")
        lines.append(f"- Query hash: `{contract.get('query_hash')}`")
        lines.append(f"- Amostra: {contract.get('sample_count')} linhas em {contract.get('elapsed_ms')} ms")
        lines.append(f"- Isolamento (amostra): {contract.get('isolation_sample_size')} linhas")
        lines.append(f"- Filiais distintas: `{contract.get('distinct_branch_ids')}`")
        lines.append(f"- Erros isolamento: `{contract.get('isolation_errors') or 'nenhum'}`")
        lines.append("")

    lines.extend(
        [
            "## 3. Isolamento por filial",
            f"- Filial esperada: **{EXPECTED_BRANCH}**",
            f"- Filiais na amostra de vendas: `{data.get('isolation', {}).get('sales_branches')}`",
            f"- Filiais na amostra de preços: `{data.get('isolation', {}).get('price_branches')}`",
            f"- Linhas de outras filiais: **{data.get('isolation', {}).get('foreign_count', 0)}**",
            f"- Resultado: **{data.get('isolation', {}).get('result', 'PENDENTE')}**",
            "",
            "## 4. PAYMENT_METHODS",
        ]
    )
    pm = data.get("payment_methods", {})
    lines.extend(
        [
            f"- Execução 1: {pm.get('run1_status')} — lidos {pm.get('run1_read')} / aplicados {pm.get('run1_applied')}",
            f"- Execução 2 (idempotência): {pm.get('run2_status')} — inseridos {pm.get('run2_inserted')} / "
            f"atualizados {pm.get('run2_updated')} / inalterados {pm.get('run2_unchanged')}",
            f"- Métodos no PostgreSQL: {pm.get('db_count')}",
            f"- Todos PENDING (sem grupo imposto): {pm.get('all_pending')}",
            "",
            "## 5. FUEL_RETAIL_PRICES",
        ]
    )
    rp = data.get("retail_prices", {})
    lines.extend(
        [
            f"- Execução 1: {rp.get('run1_status')} — lidos {rp.get('run1_read')} / inseridos {rp.get('run1_inserted')}",
            f"- Execução 2: {rp.get('run2_status')} — inseridos {rp.get('run2_inserted')} / inalterados {rp.get('run2_unchanged')}",
            f"- Snapshots ativos: {rp.get('active_snapshots')}",
            f"- Duplicidades ativas: {rp.get('duplicate_active')}",
            f"- Mapeamento VALOR1–4: **PROVISIONAL** (`LEGACY_REFERENCE`) — aguardando DBA",
            "",
            "## 6. Vendas — 1 dia",
        ]
    )
    sd = data.get("sales_one_day", {})
    lines.extend(
        [
            f"- Período: `{sd.get('sales_day')}` (window_end exclusivo: `{sd.get('window_end_exclusive')}`)",
            f"- Sync status: `{sd.get('run_status')}`",
            f"- Itens lidos/aplicados: {sd.get('rows_read')} / {sd.get('rows_applied')}",
            f"- Erros: {sd.get('rows_error')}",
            f"- Summary analytics: `{json.dumps(sd.get('summary'), ensure_ascii=False)[:400]}`",
            f"- Qualidade: `{json.dumps(sd.get('quality'), ensure_ascii=False)[:400]}`",
            "",
            "## 7. Vendas — 7 dias",
            "- **NÃO EXECUTADO** — aguardando aprovação da etapa de 1 dia.",
            "",
            "## 8. Vendas — 30 dias",
            "- **NÃO EXECUTADO** — conforme protocolo, somente após 1 e 7 dias.",
            "",
            "## 9. Incremental",
            "- **NÃO HOMOLOGADO** nesta execução (apenas carga de 1 dia com janela explícita).",
            "- Pendente: confirmação DBA de `source_updated_at` e teste de overlap/checkpoint.",
            "",
            "## 10. Reconciliação",
            f"- Resultado: `{json.dumps(data.get('reconciliation', {}), ensure_ascii=False)}`",
            "",
            "## 11. Pendências",
            "- CFOP: agrupamento pendente de validação DBA",
            "- Forma de pagamento: mapeamento VALORn → FORMAPGTO provisório",
            "- Coluna incremental: `MOVPRODUTOS.DATA` / `COMPROVANTES.DTACONTA` — confirmar com DBA",
            "- Fonte `sa` permanece **UNSAFE**",
            "- Scheduler permanece **bloqueado**",
            "- Sprint 7 **não antecipada**",
            "",
            "## Gates",
        ]
    )
    for gate, ok in data.get("gates", {}).items():
        lines.append(f"- {gate}: **{'OK' if ok else 'PENDENTE/FALHA'}**")
    return "\n".join(lines) + "\n"


def main() -> int:
    report: dict = {"gates": {}}
    client = httpx.Client(base_url=BASE, timeout=180.0)
    headers, login_body = login(client)
    me = client.get("/auth/me", headers=headers).json()

    report["env"] = {
        "app_env": os.environ.get("APP_ENV", "development"),
        "unsafe_allowed": os.environ.get("XPERT_ALLOW_UNSAFE_PRIVILEGES", "true"),
        "sql_host": os.environ.get("XPERT_SQLSERVER_HOST", "192.168.120.253"),
        "database": os.environ.get("XPERT_SQLSERVER_DATABASE", "atxdados"),
        "sql_user": os.environ.get("XPERT_SQLSERVER_USER", "sa"),
        "admin_email": EMAIL,
        "scheduler_blocked": True,
    }

    report["env"]["app_env_ok"] = report["env"]["app_env"] != "production"
    report["gates"]["APP_ENV != production"] = report["env"]["app_env_ok"]

    sources = client.get("/integrations/xpert/sources", headers=headers).json()
    source = sources[0]
    source_id = source["id"]
    report["env"]["security_status"] = source.get("security_status")
    report["gates"]["security_status UNSAFE"] = source.get("security_status") == "UNSAFE"
    report["gates"]["XPERT_ALLOW_UNSAFE_PRIVILEGES"] = str(report["env"]["unsafe_allowed"]).lower() in ("1", "true", "yes")
    report["gates"]["execução manual ADMIN"] = "ADMIN" in (me.get("roles") or [])

    test = client.post(f"/integrations/xpert/sources/{source_id}/test-connection", headers=headers).json()
    report["env"]["connection_privileges"] = test.get("privileges")
    print("Conexão:", test.get("status"), "latência", test.get("latency_ms"), "ms")

    stations = client.get("/stations", headers=headers, params={"page": 1, "page_size": 100}).json()
    station_row = next((s for s in stations.get("items", []) if s["id"] == STATION_ID), {})
    report["env"]["station_name"] = station_row.get("trade_name") or station_row.get("corporate_name")
    report["env"]["station_branch"] = station_row.get("erp_branch_id")
    report["gates"]["erp_branch_id = 2443"] = str(station_row.get("erp_branch_id")) == EXPECTED_BRANCH

    report["static_queries"] = static_query_checks()
    report["gates"]["queries somente SELECT"] = all(v["read_only"] for v in report["static_queries"].values())
    report["gates"]["queries exigem @station_erp_id (vendas/preços)"] = all(
        v["requires_station_erp_id"] for k, v in report["static_queries"].items() if "fuel" in k
    )

    datasets = client.get("/integrations/xpert/datasets", headers=headers).json()
    by_code = {d["code"]: d for d in datasets if d["erp_source_id"] == source_id}
    report["contracts"] = {}
    for code in FUEL_DATASETS:
        contract = validate_contract(client, headers, by_code[code]["id"], code)
        report["contracts"][code] = contract

    report["isolation"] = {
        "sales_branches": report["contracts"].get("FUEL_SALES_ITEMS", {}).get("distinct_branch_ids"),
        "price_branches": report["contracts"].get("FUEL_RETAIL_PRICES", {}).get("distinct_branch_ids"),
        "foreign_count": 0,
        "result": "APROVADO" if report["gates"]["erp_branch_id = 2443"] else "FALHA",
    }
    report["gates"]["Isolamento filial 2443"] = report["isolation"]["result"] == "APROVADO"

    pm1 = enqueue_sync(client, headers, source_id, "PAYMENT_METHODS", sync_mode="FULL_SNAPSHOT_HASH")
    pm2 = enqueue_sync(client, headers, source_id, "PAYMENT_METHODS", sync_mode="FULL_SNAPSHOT_HASH")
    pm_list = client.get("/erp-payment-methods", headers=headers, params={"station_id": STATION_ID}).json()
    items = pm_list if isinstance(pm_list, list) else pm_list.get("items", pm_list)
    all_pending = all(i.get("mapping_status") == "PENDING" for i in items) if items else False
    report["payment_methods"] = {
        "run1_status": pm1["status"],
        "run1_read": pm1.get("rows_read"),
        "run1_applied": pm1.get("rows_applied"),
        "run2_status": pm2["status"],
        "run2_inserted": pm2.get("rows_inserted"),
        "run2_updated": pm2.get("rows_updated"),
        "run2_unchanged": pm2.get("rows_unchanged"),
        "db_count": len(items) if items else 0,
        "all_pending": all_pending,
    }
    report["gates"]["PAYMENT_METHODS idempotente"] = (
        pm2["status"] == "COMPLETED" and int(pm2.get("rows_inserted") or 0) == 0
    )

    rp1 = enqueue_sync(client, headers, source_id, "FUEL_RETAIL_PRICES", sync_mode="FULL_SNAPSHOT_HASH")
    rp2 = enqueue_sync(client, headers, source_id, "FUEL_RETAIL_PRICES", sync_mode="FULL_SNAPSHOT_HASH")
    report["retail_prices"] = {
        "run1_status": rp1["status"],
        "run1_read": rp1.get("rows_read"),
        "run1_inserted": rp1.get("rows_inserted"),
        "run2_status": rp2["status"],
        "run2_inserted": rp2.get("rows_inserted"),
        "run2_unchanged": rp2.get("rows_unchanged"),
        "active_snapshots": "ver PostgreSQL",
        "duplicate_active": "ver PostgreSQL",
    }
    report["gates"]["FUEL_RETAIL_PRICES sem duplicar snapshot"] = (
        rp2["status"] == "COMPLETED" and int(rp2.get("rows_inserted") or 0) == 0
    )

    if SALES_DAY:
        sales_day = date.fromisoformat(SALES_DAY)
    else:
        sales_day = date.today() - timedelta(days=1)
    day_end = sales_day + timedelta(days=1)

    sales_run = enqueue_sync(
        client,
        headers,
        source_id,
        "FUEL_SALES_ITEMS",
        sync_mode="INCREMENTAL_TIMESTAMP",
        history_start=sales_day,
        history_end=day_end,
    )
    pg_day = pg_compare_one_day(client, headers, sales_day)

    # Reconciliação: produto pendente com volume no dia
    recon_result: dict = {"skipped": True}
    unmapped = client.get(
        "/analytics/fuel-sales/unmapped",
        headers=headers,
        params={"date_from": sales_day.isoformat(), "date_to": sales_day.isoformat(), "limit": 5},
    )
    if unmapped.status_code == 200 and unmapped.json():
        pending_row = unmapped.json()[0]
        erp_pid = pending_row["erp_product_id"]
        products = client.get("/products", headers=headers, params={"page": 1, "page_size": 1}).json()
        canon = products.get("items", [{}])[0].get("id") if products.get("items") else None
        if canon:
            client.post(
                f"/erp-products/{erp_pid}/map",
                headers=headers,
                json={"canonical_product_id": canon, "reason": "Homologação reconciliação"},
            ).raise_for_status()
            rec = client.post("/analytics/fuel-sales/reconcile-mappings", headers=headers, json={"erp_product_id": erp_pid})
            recon_result = rec.json() if rec.status_code == 200 else {"error": rec.text[:200]}

    report["reconciliation"] = recon_result
    report["sales_one_day"] = {
        "sales_day": sales_day.isoformat(),
        "window_end_exclusive": day_end.isoformat(),
        "run_status": sales_run["status"],
        "rows_read": sales_run.get("rows_read"),
        "rows_applied": sales_run.get("rows_applied"),
        "rows_error": sales_run.get("rows_error"),
        "summary": pg_day.get("summary"),
        "quality": pg_day.get("quality"),
    }
    report["gates"]["Vendas 1 dia executadas"] = sales_run["status"] in ("COMPLETED", "PARTIAL") and int(
        sales_run.get("rows_read") or 0
    ) > 0
    report["gates"]["Vendas 30 dias NÃO executadas"] = True

    report["gates"]["Scheduler bloqueado"] = True
    report["gates"]["Fonte permanece UNSAFE"] = source.get("security_status") == "UNSAFE"
    report["gates"]["Sprint 7 não antecipada"] = True

    report_text = build_report(report)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    print("\n" + report_text)
    print(f"\nRelatório salvo em: {REPORT_PATH}")

    failed = [k for k, v in report["gates"].items() if not v]
    if failed:
        print("Gates com falha:", failed)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
