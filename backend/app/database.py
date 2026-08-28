"""SQLite persistence for the local content service."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .catalog import EVENTS, INSTITUTIONS, PEOPLE, PORTRAIT_KEYS, REIGNS, RELATIONS, SOURCE

DATA_DIRECTORY = Path(__file__).resolve().parent.parent / "data"
DATABASE_PATH = DATA_DIRECTORY / "ming_history.sqlite3"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS source (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    citation TEXT NOT NULL,
    url TEXT NOT NULL DEFAULT '',
    review_status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reign (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL UNIQUE,
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL,
    summary TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS person (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    title TEXT NOT NULL,
    reign TEXT NOT NULL,
    years TEXT NOT NULL,
    category TEXT NOT NULL,
    courtesy_name TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL,
    biography TEXT NOT NULL,
    family_summary TEXT NOT NULL DEFAULT '',
    verification_status TEXT NOT NULL DEFAULT '未校验',
    portrait_key TEXT,
    source_id TEXT NOT NULL REFERENCES source(id)
);

CREATE TABLE IF NOT EXISTS event (
    id TEXT PRIMARY KEY,
    reign_id TEXT NOT NULL REFERENCES reign(id),
    year INTEGER NOT NULL,
    month TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    detail TEXT NOT NULL,
    place TEXT NOT NULL,
    participants TEXT NOT NULL DEFAULT '',
    consequence TEXT NOT NULL DEFAULT '',
    source_id TEXT NOT NULL REFERENCES source(id)
);

CREATE INDEX IF NOT EXISTS event_by_reign_year ON event(reign_id, year);
CREATE INDEX IF NOT EXISTS person_by_category ON person(category);

-- 对外页面只显示统一栏目；出处在本表和 content_reference 中保存，供编辑校核。
CREATE TABLE IF NOT EXISTS person_section (
    person_id TEXT NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    section_key TEXT NOT NULL,
    title TEXT NOT NULL,
    position INTEGER NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY(person_id, section_key)
);

CREATE TABLE IF NOT EXISTS event_section (
    event_id TEXT NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    section_key TEXT NOT NULL,
    title TEXT NOT NULL,
    position INTEGER NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY(event_id, section_key)
);

CREATE TABLE IF NOT EXISTS content_reference (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_type TEXT NOT NULL CHECK(content_type IN ('person', 'event')),
    content_id TEXT NOT NULL,
    section_key TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    title TEXT NOT NULL,
    url TEXT NOT NULL DEFAULT '',
    locator TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    UNIQUE(content_type, content_id, section_key, position)
);

CREATE INDEX IF NOT EXISTS content_reference_by_content
    ON content_reference(content_type, content_id, section_key);

-- 外部检索过程只作编辑审计；用户端仍只显示“已校验”或“未校验”。
CREATE TABLE IF NOT EXISTS person_research (
    person_id TEXT NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('matched', 'not_found', 'identity_rejected', 'network_failed')),
    entity_id TEXT NOT NULL DEFAULT '',
    checked_at TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    PRIMARY KEY(person_id, provider)
);

CREATE INDEX IF NOT EXISTS person_research_by_status
    ON person_research(provider, status);

CREATE TABLE IF NOT EXISTS person_relation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_person_id TEXT NOT NULL REFERENCES person(id),
    to_person_id TEXT NOT NULL REFERENCES person(id),
    relation_type TEXT NOT NULL,
    reign TEXT NOT NULL,
    note TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES source(id),
    UNIQUE(from_person_id, to_person_id, relation_type, reign)
);

CREATE TABLE IF NOT EXISTS institution (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    active_reigns TEXT NOT NULL,
    function TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES source(id)
);

CREATE TABLE IF NOT EXISTS institution_promotion (
    institution_id TEXT NOT NULL REFERENCES institution(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    label TEXT NOT NULL,
    PRIMARY KEY(institution_id, position)
);

CREATE TABLE IF NOT EXISTS institution_reform (
    institution_id TEXT NOT NULL REFERENCES institution(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    year TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    PRIMARY KEY(institution_id, position)
);
"""


def connect() -> sqlite3.Connection:
    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    """Create the normalized content store and safely synchronize the editorial catalog."""

    with connect() as connection:
        connection.executescript(SCHEMA)
        _migrate_person_columns(connection)
        connection.executemany(
            """
            INSERT INTO source(id, title, citation, url, review_status) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                citation = excluded.citation,
                url = excluded.url,
                review_status = excluded.review_status
            """,
            [
                tuple(source[key] for key in ("id", "title", "citation", "url", "review_status"))
                for source in (SOURCE,)
            ],
        )
        connection.executemany(
            """
            INSERT INTO reign(id, title, start_year, end_year, summary)
            VALUES (:id, :title, :start_year, :end_year, :summary)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                start_year = excluded.start_year,
                end_year = excluded.end_year,
                summary = excluded.summary
            """,
            REIGNS,
        )

        source_id = SOURCE["id"]
        # 编目库已不含 CBDB 索引导入条目；清理历史库中残留的 CBDB 数据及其关联审计记录。
        connection.execute("DELETE FROM person_research WHERE person_id LIKE 'cbdb-%'")
        connection.execute("DELETE FROM person_section WHERE person_id LIKE 'cbdb-%'")
        connection.execute("DELETE FROM content_reference WHERE content_type = 'person' AND content_id LIKE 'cbdb-%'")
        connection.execute("DELETE FROM person WHERE source_id = 'cbdb-20210525'")
        connection.executemany(
            """
            INSERT INTO person(id, name, title, reign, years, category, courtesy_name, summary, biography, family_summary, source_id)
            VALUES (:id, :name, :title, :reign, :years, :category, :courtesy_name, :summary, :biography, :family_summary, :source_id)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                title = excluded.title,
                reign = excluded.reign,
                years = excluded.years,
                category = excluded.category,
                courtesy_name = excluded.courtesy_name,
                summary = excluded.summary,
                biography = CASE
                    WHEN EXISTS (
                        SELECT 1 FROM person_section
                        WHERE person_id = person.id AND section_key = 'life'
                    ) THEN person.biography
                    ELSE excluded.biography
                END,
                source_id = excluded.source_id
            """,
            [{**person, "family_summary": "", "source_id": source_id} for person in PEOPLE],
        )
        connection.executemany(
            """
            INSERT INTO event(id, reign_id, year, month, title, summary, detail, place, participants, consequence, source_id)
            VALUES (:id, :reign_id, :year, :month, :title, :summary, :detail, :place, :participants, :consequence, :source_id)
            ON CONFLICT(id) DO UPDATE SET
                reign_id = excluded.reign_id,
                year = excluded.year,
                month = excluded.month,
                title = excluded.title,
                summary = excluded.summary,
                detail = excluded.detail,
                place = excluded.place,
                participants = excluded.participants,
                consequence = excluded.consequence,
                source_id = excluded.source_id
            """,
            [{**event, "source_id": source_id} for event in EVENTS],
        )
        connection.executemany(
            """
            INSERT INTO person_relation(from_person_id, to_person_id, relation_type, reign, note, source_id)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(from_person_id, to_person_id, relation_type, reign) DO UPDATE SET
                note = excluded.note,
                source_id = excluded.source_id
            """,
            [(*relation, source_id) for relation in RELATIONS],
        )

        for institution in INSTITUTIONS:
            connection.execute(
                """
                INSERT INTO institution(id, name, category, active_reigns, function, source_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    category = excluded.category,
                    active_reigns = excluded.active_reigns,
                    function = excluded.function,
                    source_id = excluded.source_id
                """,
                (
                    institution["id"],
                    institution["name"],
                    institution["category"],
                    institution["active_reigns"],
                    institution["function"],
                    source_id,
                ),
            )
            connection.executemany(
                """
                INSERT INTO institution_promotion(institution_id, position, label) VALUES (?, ?, ?)
                ON CONFLICT(institution_id, position) DO UPDATE SET label = excluded.label
                """,
                [(institution["id"], position, label) for position, label in enumerate(institution["promotion_path"])],
            )
            connection.executemany(
                """
                INSERT INTO institution_reform(institution_id, position, year, title, description)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(institution_id, position) DO UPDATE SET
                    year = excluded.year,
                    title = excluded.title,
                    description = excluded.description
                """,
                [
                    (institution["id"], position, year, title, description)
                    for position, (year, title, description) in enumerate(institution["reforms"])
                ],
            )
        _apply_asset_metadata(connection)


def _migrate_person_columns(connection: sqlite3.Connection) -> None:
    """Apply additive SQLite migrations for databases created by earlier app versions."""

    columns = {row[1] for row in connection.execute("PRAGMA table_info(person)")}
    if "family_summary" not in columns:
        connection.execute("ALTER TABLE person ADD COLUMN family_summary TEXT NOT NULL DEFAULT ''")
    if "verification_status" not in columns:
        connection.execute("ALTER TABLE person ADD COLUMN verification_status TEXT NOT NULL DEFAULT '未校验'")


def _apply_asset_metadata(connection: sqlite3.Connection) -> None:
    """Synchronize metadata that is packaged with the Android client."""

    connection.executemany(
        "UPDATE person SET portrait_key = ? WHERE id = ?",
        [(key, person_id) for person_id, key in PORTRAIT_KEYS.items()],
    )
