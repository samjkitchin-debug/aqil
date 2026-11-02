"""Promote one accepted parameter version without copying a historical run."""

from __future__ import annotations

import json
from dataclasses import dataclass

import psycopg

from aqil_research.methods.stock_watson_accepted import (
    ESTIMATION,
    METHOD_ID,
    METHOD_VERSION,
    PARAMETER_VERSION_ID,
    PROVENANCE_RUN_ID,
    PUBLICATION_ALLOWED,
    accepted_parameter_checksum,
    accepted_parameter_values,
    parameter_identity_ok,
)


class ParameterPromotionRefused(RuntimeError):
    """The parameter artifact does not match the accepted version."""


@dataclass(frozen=True, slots=True)
class ParameterPromotion:
    status: str
    parameter_version_id: str
    checksum: str


def promote_accepted_parameter_version(conn: psycopg.Connection) -> ParameterPromotion:
    """Insert the accepted vector once. A matching checksum does not write again."""
    if PUBLICATION_ALLOWED:
        raise ParameterPromotionRefused("publication_allowed must stay false")
    values = accepted_parameter_values()
    if not parameter_identity_ok(values):
        raise ParameterPromotionRefused("the accepted parameter identity check failed")
    checksum = accepted_parameter_checksum()
    if "filtered_factor" in values or "smoothed_factor" in values:
        raise ParameterPromotionRefused("a parameter artifact must not contain a factor path")
    existing = conn.execute(
        """
        select checksum, parameter_values
        from research.parameter_versions
        where parameter_version_id = %s
        """,
        (PARAMETER_VERSION_ID,),
    ).fetchone()
    if existing is not None:
        if existing[0] != checksum or not parameter_identity_ok(existing[1]):
            raise ParameterPromotionRefused(
                "this parameter version id is already stored with different values"
            )
        return ParameterPromotion("unchanged", PARAMETER_VERSION_ID, checksum)
    conn.execute(
        """
        insert into research.parameter_versions (
          parameter_version_id, method_id, method_version, checksum,
          parameter_values, estimation_configuration, provenance_run_id,
          publication_allowed, operationally_accepted
        ) values (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, false, false)
        """,
        (
            PARAMETER_VERSION_ID,
            METHOD_ID,
            METHOD_VERSION,
            checksum,
            json.dumps(values, sort_keys=True),
            json.dumps(ESTIMATION, sort_keys=True),
            PROVENANCE_RUN_ID,
        ),
    )
    return ParameterPromotion("promoted", PARAMETER_VERSION_ID, checksum)


def load_accepted_factor_parameters(conn: psycopg.Connection) -> dict[str, object] | None:
    """Parameter table first. A preserved run is only the fallback."""
    if _table_ready(conn):
        row = conn.execute(
            """
            select parameter_values, checksum
            from research.parameter_versions
            where method_id = %s and publication_allowed is false
            order by recorded_at desc
            limit 1
            """,
            (METHOD_ID,),
        ).fetchone()
        if row is not None and isinstance(row[0], dict):
            if row[1] != accepted_parameter_checksum() or not parameter_identity_ok(row[0]):
                raise ParameterPromotionRefused("stored parameter checksum does not match")
            return dict(row[0])
    return _adopted_run_parameters(conn)


def latest_filtered_calculation(conn: psycopg.Connection) -> dict[str, object] | None:
    """Latest stored path. A calculation is not selected as the parameter version."""
    row = conn.execute(
        """
        select calculation
        from research.research_runs
        where method_id = %s
          and execution_status = 'completed'
          and calculation ? 'filtered_factor'
        order by executed_at desc
        limit 1
        """,
        (METHOD_ID,),
    ).fetchone()
    if row is None or not isinstance(row[0], dict):
        return None
    return row[0]


def _table_ready(conn: psycopg.Connection) -> bool:
    row = conn.execute("select to_regclass('research.parameter_versions')").fetchone()
    return bool(row and row[0])


def _adopted_run_parameters(conn: psycopg.Connection) -> dict[str, object] | None:
    row = conn.execute(
        """
        select calculation
        from research.research_runs
        where method_id = %s
          and execution_status = 'completed'
          and calculation ? 'loadings_ip_income_sales_payroll'
          and coalesce(calculation->>'adopted_parameter_version', 'true') = 'true'
          and run_id <> '940955f1-50d5-4c06-9d90-5ceebd05d352'
        order by executed_at desc
        limit 1
        """,
        (METHOD_ID,),
    ).fetchone()
    if row is None or not isinstance(row[0], dict):
        return None
    calculation = row[0]
    required = (
        "loadings_ip_income_sales_payroll",
        "factor_ar",
        "idiosyncratic_ar",
        "idiosyncratic_scale",
    )
    if any(key not in calculation for key in required):
        return None
    parameters: dict[str, object] = {key: calculation[key] for key in required}
    moments = calculation.get("moments")
    if isinstance(moments, dict):
        parameters["moments"] = moments
    return parameters
