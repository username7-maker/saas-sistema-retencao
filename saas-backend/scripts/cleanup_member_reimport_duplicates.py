import argparse
import json
import os
from dataclasses import dataclass

from sqlalchemy import create_engine, text


MAPPING_SQL = """
create temporary table tmp_member_reimport_mapping on commit drop as
with suspect as (
    select
        m.id as suspect_id,
        m.gym_id,
        lower(trim(m.full_name)) as name_key,
        m.created_at
    from members m
    join gyms g on g.id = m.gym_id
    where g.slug = :gym_slug
      and m.deleted_at is null
      and m.created_at >= cast(:created_after as timestamptz)
      and (m.email is null or trim(m.email) = '')
      and coalesce(m.extra_data->>'external_id', '') = ''
      and exists (
          select 1
          from members older
          where older.gym_id = m.gym_id
            and older.deleted_at is null
            and older.id <> m.id
            and lower(trim(older.full_name)) = lower(trim(m.full_name))
            and older.created_at < m.created_at
      )
), ranked as (
    select
        s.suspect_id,
        c.id as canonical_id,
        row_number() over (
            partition by s.suspect_id
            order by
                case when c.email is not null and trim(c.email) <> '' then 1 else 0 end desc,
                case when coalesce(c.extra_data->>'external_id', '') <> '' then 1 else 0 end desc,
                case when c.last_checkin_at is not null then 1 else 0 end desc,
                c.created_at asc,
                c.id asc
        ) as rn
    from suspect s
    join members c
      on c.gym_id = s.gym_id
     and c.deleted_at is null
     and lower(trim(c.full_name)) = s.name_key
     and c.created_at < s.created_at
)
select suspect_id, canonical_id
from ranked
where rn = 1
"""


SUMMARY_SQL = """
select
    (select count(*) from tmp_member_reimport_mapping) as suspect_members,
    (select count(*) from checkins c join tmp_member_reimport_mapping m on m.suspect_id = c.member_id) as suspect_checkins,
    (
        select count(*)
        from checkins c
        join tmp_member_reimport_mapping m on m.suspect_id = c.member_id
        where exists (
            select 1
            from checkins existing
            where existing.member_id = m.canonical_id
              and existing.checkin_at = c.checkin_at
        )
    ) as checkin_collisions,
    (select count(*) from risk_alerts ra join tmp_member_reimport_mapping m on m.suspect_id = ra.member_id) as suspect_risk_alerts,
    (select count(*) from tasks t join tmp_member_reimport_mapping m on m.suspect_id = t.member_id and t.deleted_at is null) as suspect_tasks,
    (select count(*) from assessments a join tmp_member_reimport_mapping m on m.suspect_id = a.member_id and a.deleted_at is null) as suspect_assessments
"""


APPLY_SQL = [
    (
        "move_checkins",
        """
        update checkins c
        set member_id = m.canonical_id
        from tmp_member_reimport_mapping m
        where c.member_id = m.suspect_id
          and not exists (
              select 1
              from checkins existing
              where existing.member_id = m.canonical_id
                and existing.checkin_at = c.checkin_at
          )
        """,
    ),
    (
        "delete_remaining_suspect_checkins",
        """
        delete from checkins c
        using tmp_member_reimport_mapping m
        where c.member_id = m.suspect_id
        """,
    ),
    (
        "delete_suspect_risk_alerts",
        """
        delete from risk_alerts ra
        using tmp_member_reimport_mapping m
        where ra.member_id = m.suspect_id
        """,
    ),
    (
        "refresh_canonical_last_checkin",
        """
        update members member_row
        set last_checkin_at = src.max_checkin_at
        from (
            select c.member_id, max(c.checkin_at) as max_checkin_at
            from checkins c
            join (
                select distinct canonical_id
                from tmp_member_reimport_mapping
            ) mapped on mapped.canonical_id = c.member_id
            group by c.member_id
        ) src
        where member_row.id = src.member_id
          and (member_row.last_checkin_at is null or member_row.last_checkin_at < src.max_checkin_at)
        """,
    ),
    (
        "soft_delete_suspects",
        """
        update members m
        set deleted_at = now(), updated_at = now()
        from tmp_member_reimport_mapping map_row
        where m.id = map_row.suspect_id
          and m.deleted_at is null
        """,
    ),
]


@dataclass
class CleanupSummary:
    suspect_members: int
    suspect_checkins: int
    checkin_collisions: int
    suspect_risk_alerts: int
    suspect_tasks: int
    suspect_assessments: int


def _require_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("DATABASE_URL nao encontrada no ambiente.")
    return database_url


def _load_summary(connection, *, gym_slug: str, created_after: str) -> CleanupSummary:
    connection.execute(text("drop table if exists tmp_member_reimport_mapping"))
    connection.execute(text(MAPPING_SQL), {"gym_slug": gym_slug, "created_after": created_after})
    row = connection.execute(text(SUMMARY_SQL)).mappings().one()
    return CleanupSummary(**{key: int(value or 0) for key, value in row.items()})


def _print_summary(summary: CleanupSummary) -> None:
    print(
        json.dumps(
            {
                "suspect_members": summary.suspect_members,
                "suspect_checkins": summary.suspect_checkins,
                "checkin_collisions": summary.checkin_collisions,
                "suspect_risk_alerts": summary.suspect_risk_alerts,
                "suspect_tasks": summary.suspect_tasks,
                "suspect_assessments": summary.suspect_assessments,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean duplicate members caused by repeated member reimports.")
    parser.add_argument("--gym-slug", required=True, help="Gym slug to clean.")
    parser.add_argument(
        "--created-after",
        required=True,
        help="Only inspect members created on/after this UTC timestamp.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply cleanup. Default mode is dry-run.",
    )
    args = parser.parse_args()

    engine = create_engine(_require_database_url(), future=True)

    with engine.begin() as connection:
        summary = _load_summary(connection, gym_slug=args.gym_slug, created_after=args.created_after)
        print("CLEANUP_SUMMARY")
        _print_summary(summary)

        if summary.suspect_tasks or summary.suspect_assessments:
            raise SystemExit("Cleanup aborted: suspect members already have tasks or assessments linked.")

        if not args.apply:
            print("DRY_RUN_ONLY")
            return

        results: dict[str, int] = {}
        for label, sql in APPLY_SQL:
            result = connection.execute(text(sql))
            results[label] = int(result.rowcount or 0)

        print("APPLY_RESULTS")
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
