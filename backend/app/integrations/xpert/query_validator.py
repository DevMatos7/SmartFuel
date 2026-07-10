from __future__ import annotations

import re
from dataclasses import dataclass

import sqlglot
from sqlglot import exp

ALLOWED_PARAMETERS = {
    "station_erp_id",
    "window_start",
    "window_end",
    "last_source_id",
    "batch_limit",
}

_FORBIDDEN_NODE_NAMES = {
    "Insert",
    "Update",
    "Delete",
    "Merge",
    "Drop",
    "Create",
    "Alter",
    "Grant",
    "Revoke",
    "Truncate",
    "Command",
    "Execute",
    "Transaction",
    "Commit",
    "Rollback",
}


@dataclass
class QueryValidationResult:
    valid: bool
    errors: list[str]
    normalized_sql: str | None = None


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql


def _root_is_read_select(expression: exp.Expression) -> bool:
    if isinstance(expression, exp.Select):
        return True
    if isinstance(expression, exp.Union):
        return all(
            isinstance(arg, exp.Expression) and _root_is_read_select(arg)
            for arg in expression.args.values()
            if isinstance(arg, exp.Expression)
        )
    if isinstance(expression, exp.Subquery):
        return _root_is_read_select(expression.this)
    if isinstance(expression, exp.With):
        for cte in expression.expressions:
            if isinstance(cte, exp.CTE) and not _root_is_read_select(cte.this):
                return False
        return _root_is_read_select(expression.this)
    return False


def validate_read_only_query(sql: str) -> QueryValidationResult:
    errors: list[str] = []
    stripped = _strip_comments(sql).strip()
    if not stripped:
        return QueryValidationResult(valid=False, errors=["Query vazia."])

    body = stripped.rstrip(";").strip()
    if ";" in body:
        errors.append("Múltiplos statements não são permitidos.")

    if re.search(r"\$\{|\+\s*['\"]|f['\"]", stripped):
        errors.append("Interpolação de string não é permitida.")

    try:
        expressions = sqlglot.parse(body, read="tsql")
    except Exception as exc:
        return QueryValidationResult(valid=False, errors=[f"SQL inválido: {exc}"])

    if len(expressions) != 1:
        errors.append("Múltiplos statements não são permitidos.")
        return QueryValidationResult(valid=not errors, errors=errors)

    expression = expressions[0]
    if not _root_is_read_select(expression):
        errors.append("Somente SELECT ou WITH ... SELECT são permitidos.")

    for node in expression.walk():
        node_name = type(node).__name__
        if node_name in _FORBIDDEN_NODE_NAMES:
            errors.append(f"Comando proibido detectado: {node_name}")
        if isinstance(node, exp.Into):
            errors.append("SELECT INTO não é permitido.")
        if isinstance(node, exp.Anonymous) and str(node.this).upper() in {"EXEC", "EXECUTE", "SP_EXECUTESQL"}:
            errors.append("SQL dinâmico ou EXEC não são permitidos.")

    return QueryValidationResult(valid=not errors, errors=errors, normalized_sql=body)


def extract_parameters(sql: str) -> set[str]:
    return set(re.findall(r"@([a-zA-Z_][a-zA-Z0-9_]*)", sql))


def validate_parameters(sql: str) -> list[str]:
    params = extract_parameters(sql)
    unknown = sorted(params - ALLOWED_PARAMETERS)
    if unknown:
        return [f"Parâmetro não permitido: @{name}" for name in unknown]
    return []
