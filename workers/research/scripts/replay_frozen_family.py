"""Replay one stored run per family on the disposable database.

Reads local postgres. Writes only inside a transaction on aqil_research_test,
then rolls that transaction back. Does not reset postgres and does not open
the hosted project.
"""

from __future__ import annotations

import psycopg

from aqil_research.persistence.reproduce import classify_historical_replay
from aqil_research.persistence.runs import load_research_run, save_research_run

SOURCE = "postgresql://research_worker:research_worker@127.0.0.1:55432/postgres"
TARGET = "postgresql://research_worker:research_worker@127.0.0.1:55432/aqil_research_test"

RUNS = (
    "3955f7f4-08f8-4e7b-9ded-b3f6eea6633f",
    "a7a2620a-7bd9-4cca-917b-992062ab025c",
    "3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a",
    "940955f1-50d5-4c06-9d90-5ceebd05d352",
    "4629b31d-b0de-4a2f-a987-9e5d3f94747e",
    "2f4c14eb-44f2-40dc-913f-bf7945e972cd",
    "7c33c9b1-3759-4fa6-86ea-c0bcbc86257e",
    "bcbf15bc-590e-4738-9bc1-bbe951b12079",
    "e340659b-b693-480a-8e6d-a64b24b90f99",
    "137d92b7-6ce1-49eb-82ad-8f5727b00f90",
    "adff8815-8582-4c2e-befa-5faef3f9b925",
    "1f747c9f-4851-4588-a4dc-d8fb1ff30558",
    "625e94dc-5bc5-4f4b-a01a-9c3816b9d0c6",
    "18f5d7bb-8227-4441-8b45-6755153d7b8f",
    "06ff435b-2279-4a46-99cb-6a99dd4f0a35",
    "e399de3f-18a6-4a72-b41f-6d14611b4338",
    "b4f95b41-cc0c-4b38-9792-d866abd6e54d",
    "f3db281d-9f6d-4c4c-974f-ba4b9bd68131",
    "cbfdaf86-8446-435e-8ceb-7f43557613f1",
)


def main() -> None:
    with psycopg.connect(SOURCE) as source, psycopg.connect(TARGET) as target:
        source.execute("set default_transaction_read_only = on")
        identity = target.execute("select current_database()").fetchone()
        if identity is None or identity[0] != "aqil_research_test":
            raise RuntimeError("refusing to replay outside aqil_research_test")
        for run_id in RUNS:
            target.rollback()
            stored = load_research_run(source, run_id)
            _copy_inputs(source, target, stored.observation_ids)
            save_research_run(target, stored)
            classified = classify_historical_replay(target, run_id)
            print(
                stored.method_id,
                run_id,
                classified.outcome,
                classified.missing_field or "",
                "; ".join(classified.differences[:6]),
                "; ".join(classified.notes[:4]),
            )
            target.rollback()


def _copy_inputs(
    source: psycopg.Connection, target: psycopg.Connection, observation_ids: list[str]
) -> None:
    if not observation_ids:
        return
    retrievals = source.execute(
        """
        select distinct retrieval_id
        from research.economic_observations
        where observation_id = any(%s)
        """,
        (observation_ids,),
    ).fetchall()
    retrieval_ids = [row[0] for row in retrievals]
    _copy_table(
        source,
        target,
        "research.source_retrievals",
        "retrieval_id = any(%s)",
        (retrieval_ids,),
    )
    _copy_table(
        source,
        target,
        "research.economic_observations",
        "observation_id = any(%s)",
        (observation_ids,),
    )


def _copy_table(
    source: psycopg.Connection,
    target: psycopg.Connection,
    table: str,
    where: str,
    params: tuple[object, ...],
) -> None:
    schema, name = table.split(".")
    jsonb = {
        row[0]
        for row in source.execute(
            """
            select column_name
            from information_schema.columns
            where table_schema = %s and table_name = %s and udt_name = 'jsonb'
            """,
            (schema, name),
        ).fetchall()
    }
    with source.cursor() as cur:
        cur.execute(f"select * from {table} where {where}", params)
        rows = cur.fetchall()
        columns = [item.name for item in cur.description]
    if not rows:
        return
    adapted = [
        tuple(
            _adapt(value) if column in jsonb else value
            for column, value in zip(columns, row, strict=True)
        )
        for row in rows
    ]
    placeholders = ", ".join(["%s"] * len(columns))
    names = ", ".join(columns)
    statement = f"insert into {table} ({names}) values ({placeholders}) on conflict do nothing"
    with target.cursor() as cur:
        cur.executemany(statement, adapted)


def _adapt(value: object) -> object:
    if isinstance(value, (dict, list)):
        return psycopg.types.json.Json(value)
    return value


if __name__ == "__main__":
    main()
