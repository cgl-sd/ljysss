"""SQLite persistence for the local content service."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from .catalog import EVENTS, INSTITUTIONS, PEOPLE, PORTRAIT_KEYS, REIGNS, RELATIONS, SOURCE, SPECIAL_ITEMS

DATA_DIRECTORY = Path(__file__).resolve().parent.parent / "data"
DATABASE_PATH = DATA_DIRECTORY / "ming_history.sqlite3"
# 二进制库适合运行期读写、不适合进版本库；内容真相按表存成一行一条的 JSONL。
CONTENT_DIRECTORY = DATA_DIRECTORY / "content"

# 插入顺序即外键依赖顺序，导出与导入共用。
CONTENT_TABLES = [
    "source",
    "reign",
    "person_category",
    "person",
    "event",
    "event_section",
    "person_section_definition",
    "person_section",
    "content_reference",
    "person_research",
    "person_relation",
    "person_kin",
    "event_participant",
    "annal",
    "annal_participant",
    "institution",
    "institution_promotion",
    "institution_reform",
    "institution_section",
    "institution_person",
    "special_item",
    "special_section",
    "special_person",
    "person_mingshi",
    "person_wiki",
    "person_cbdb",
]

# 行序决定文本的 diff 稳定性：按主键或业务键排序，不依赖 SQLite 的物理顺序。
CONTENT_ORDER = {
    "person_category": ("position",),
    "person_section_definition": ("position",),
    "person_relation": ("from_person_id", "to_person_id", "relation_type", "reign"),
    "person_section": ("person_id", "position"),
    "event_section": ("event_id", "position"),
    "content_reference": ("content_type", "content_id", "section_key", "position"),
    "person_research": ("person_id", "provider"),
    "person_kin": ("person_id", "relation", "kin_name"),
    "event_participant": ("event_id", "person_id"),
    "annal": ("year", "juan", "id"),
    "annal_participant": ("annal_id", "person_id"),
    "institution_promotion": ("institution_id", "position"),
    "institution_reform": ("institution_id", "position"),
    "institution_section": ("institution_id", "position"),
    "institution_person": ("institution_id", "position"),
    "special_section": ("special_item_id", "position"),
    "special_person": ("special_item_id", "position"),
}

# 人物分类和详情栏目都是内容模型的一部分，而不是前端散落的字面量。person 表仍保留
# 中文 category 列，便于既有 Android 客户端直接筛选；写入触发器会要求其对应这里的标签。
PERSON_CATEGORIES = (
    ("emperor", "帝王", 0, "在位君主与南明监国。"),
    ("inner-court", "内廷", 1, "宫中的后妃、宫人、乳母与宦官。"),
    ("imperial-clan", "宗藩", 2, "皇室宗亲、藩王与公主；不以爵位作为归类理由。"),
    ("official", "朝臣", 3, "参与中枢、地方或朝廷政治的非军事人物。"),
    ("general", "将帅", 4, "统兵将领及其他军事人物。"),
    ("literary", "文苑", 5, "未任高阶官职、以文艺、学术、医术等成就为主的人物。"),
)

PERSON_SECTION_DEFINITIONS = (
    ("life", "生平", 0, "按时间叙述人物经历，保留完整叙事段落。"),
    ("family", "家族", 1, "亲属、婚姻与子嗣，以及相关成员结局。"),
    ("relations", "人物关系", 2, "本人直接相关的非亲子关系；帝王不展示与文臣、将帅的关系。"),
    ("events", "相关事件", 3, "人物参与事件，按年份升序编排。"),
)

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

CREATE TABLE IF NOT EXISTS person_category (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL UNIQUE,
    position INTEGER NOT NULL UNIQUE,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS person (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    reign TEXT NOT NULL,
    archive_start_year INTEGER NOT NULL DEFAULT 0,
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
    -- year is the documented starting year, retained for the existing timeline index.
    year INTEGER NOT NULL,
    -- 0 is accepted only while importing a legacy JSONL row and is normalized to year.
    end_year INTEGER NOT NULL DEFAULT 0 CHECK(end_year = 0 OR end_year >= year),
    month TEXT NOT NULL,
    title TEXT NOT NULL,
    event_type TEXT NOT NULL DEFAULT '未分类',
    summary TEXT NOT NULL,
    detail TEXT NOT NULL,
    place TEXT NOT NULL,
    participants TEXT NOT NULL DEFAULT '',
    consequence TEXT NOT NULL DEFAULT '',
    source_id TEXT NOT NULL REFERENCES source(id)
);

CREATE INDEX IF NOT EXISTS event_by_reign_year ON event(reign_id, year);
CREATE INDEX IF NOT EXISTS person_by_category ON person(category);
CREATE INDEX IF NOT EXISTS person_by_category_reign_name ON person(category, reign, name);

CREATE TABLE IF NOT EXISTS person_section_definition (
    section_key TEXT PRIMARY KEY CHECK(section_key IN ('life', 'family', 'relations', 'events')),
    title TEXT NOT NULL UNIQUE,
    position INTEGER NOT NULL UNIQUE CHECK(position BETWEEN 0 AND 3),
    description TEXT NOT NULL
);

-- 对外页面只显示统一栏目；出处在本表和 content_reference 中保存，供编辑校核。
CREATE TABLE IF NOT EXISTS person_section (
    person_id TEXT NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    -- 只有这四栏会出现在人物详情上；内部标记（如资料状态）不得作为栏目存这里
    section_key TEXT NOT NULL CHECK(section_key IN ('life', 'family', 'relations', 'events')),
    title TEXT NOT NULL,
    position INTEGER NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY(person_id, section_key)
);
CREATE INDEX IF NOT EXISTS person_section_by_person_position ON person_section(person_id, position);

-- SQLite 不能为既有 person 表追加外键，故以触发器同时约束新库与旧库升级后的写入。
CREATE TRIGGER IF NOT EXISTS person_category_must_be_registered
BEFORE INSERT ON person
WHEN NOT EXISTS (SELECT 1 FROM person_category WHERE label = NEW.category)
BEGIN
    SELECT RAISE(ABORT, 'person.category must be a registered person_category label');
END;

CREATE TRIGGER IF NOT EXISTS person_category_update_must_be_registered
BEFORE UPDATE OF category ON person
WHEN NOT EXISTS (SELECT 1 FROM person_category WHERE label = NEW.category)
BEGIN
    SELECT RAISE(ABORT, 'person.category must be a registered person_category label');
END;

CREATE TRIGGER IF NOT EXISTS person_section_must_match_definition
BEFORE INSERT ON person_section
WHEN NOT EXISTS (
    SELECT 1 FROM person_section_definition
    WHERE section_key = NEW.section_key AND title = NEW.title AND position = NEW.position
)
BEGIN
    SELECT RAISE(ABORT, 'person_section must use a registered section definition');
END;

CREATE TRIGGER IF NOT EXISTS person_section_update_must_match_definition
BEFORE UPDATE OF section_key, title, position ON person_section
WHEN NOT EXISTS (
    SELECT 1 FROM person_section_definition
    WHERE section_key = NEW.section_key AND title = NEW.title AND position = NEW.position
)
BEGIN
    SELECT RAISE(ABORT, 'person_section must use a registered section definition');
END;

CREATE TABLE IF NOT EXISTS event_section (
    event_id TEXT NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    section_key TEXT NOT NULL CHECK(section_key IN ('background', 'course', 'people', 'result', 'impact')),
    title TEXT NOT NULL,
    position INTEGER NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY(event_id, section_key)
);

CREATE TABLE IF NOT EXISTS content_reference (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_type TEXT NOT NULL CHECK(content_type IN ('person', 'event', 'institution', 'special')),
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

-- 亲属与子嗣：与生平同级的一等数据。对方已在库内则记 kin_person_id 供跳转，
-- 否则只留姓名；source 记这条出自 CBDB 亲属记录还是《明史》本传。
CREATE TABLE IF NOT EXISTS person_kin (
    person_id TEXT NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    kin_person_id TEXT REFERENCES person(id) ON DELETE CASCADE,
    kin_name TEXT NOT NULL,
    relation TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    UNIQUE(person_id, kin_name, relation)
);

CREATE INDEX IF NOT EXISTS person_kin_by_person ON person_kin(person_id, relation);

-- 事件参与人：取代 event.participants 的姓名串，同名不同人靠 person_id 区分。
CREATE TABLE IF NOT EXISTS event_participant (
    event_id TEXT NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    person_id TEXT NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT '参与',
    UNIQUE(event_id, person_id)
);

CREATE INDEX IF NOT EXISTS event_participant_by_person ON event_participant(person_id);

-- 《明史》本纪逐月编年：一句话一条的编年条目，与「事件专条」不同级，
-- 不套背景/经过/结果/影响模板，只作系年事实与人物行迹的原料。
CREATE TABLE IF NOT EXISTS annal (
    id TEXT PRIMARY KEY,
    juan INTEGER NOT NULL,
    emperor TEXT NOT NULL DEFAULT '',
    reign_id TEXT NOT NULL REFERENCES reign(id),
    year INTEGER NOT NULL,
    month TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS annal_by_year ON annal(year, juan);

CREATE TABLE IF NOT EXISTS annal_participant (
    annal_id TEXT NOT NULL REFERENCES annal(id) ON DELETE CASCADE,
    person_id TEXT NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    UNIQUE(annal_id, person_id)
);

CREATE INDEX IF NOT EXISTS annal_participant_by_person ON annal_participant(person_id);

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
    track TEXT NOT NULL DEFAULT '常见任用路径',
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

-- 机构详情由稳定的正文分栏组成；正文和代表人物都保留各自来源登记，前端不显示审核状态。
CREATE TABLE IF NOT EXISTS institution_section (
    institution_id TEXT NOT NULL REFERENCES institution(id) ON DELETE CASCADE,
    section_key TEXT NOT NULL CHECK(section_key IN ('duty', 'structure', 'operation', 'evolution')),
    title TEXT NOT NULL,
    position INTEGER NOT NULL,
    content TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES source(id),
    PRIMARY KEY(institution_id, section_key)
);
CREATE INDEX IF NOT EXISTS institution_section_by_institution_position
    ON institution_section(institution_id, position);

CREATE TABLE IF NOT EXISTS institution_person (
    institution_id TEXT NOT NULL REFERENCES institution(id) ON DELETE CASCADE,
    person_id TEXT NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    position INTEGER NOT NULL,
    source_id TEXT NOT NULL REFERENCES source(id),
    PRIMARY KEY(institution_id, person_id)
);
CREATE INDEX IF NOT EXISTS institution_person_by_institution_position
    ON institution_person(institution_id, position);

-- 天下页的“典章”科普：宫殿、器物与制度名物，与机构分列。
CREATE TABLE IF NOT EXISTS special_item (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    era TEXT NOT NULL,
    description TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    source_id TEXT NOT NULL REFERENCES source(id)
);

-- 典章同样使用稳定正文分栏；机构、制度、器物和宫陵不再只是一张摘要卡片。
CREATE TABLE IF NOT EXISTS special_section (
    special_item_id TEXT NOT NULL REFERENCES special_item(id) ON DELETE CASCADE,
    section_key TEXT NOT NULL CHECK(section_key IN ('meaning', 'form', 'practice', 'legacy')),
    title TEXT NOT NULL,
    position INTEGER NOT NULL,
    content TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES source(id),
    PRIMARY KEY(special_item_id, section_key)
);
CREATE INDEX IF NOT EXISTS special_section_by_item_position
    ON special_section(special_item_id, position);

CREATE TABLE IF NOT EXISTS special_person (
    special_item_id TEXT NOT NULL REFERENCES special_item(id) ON DELETE CASCADE,
    person_id TEXT NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    position INTEGER NOT NULL,
    source_id TEXT NOT NULL REFERENCES source(id),
    PRIMARY KEY(special_item_id, person_id)
);
CREATE INDEX IF NOT EXISTS special_person_by_item_position
    ON special_person(special_item_id, position);

-- 维基百科条目全文（hf-mirror 数据包提取，t2s 规范化）。
CREATE TABLE IF NOT EXISTS person_wiki (
    person_id TEXT PRIMARY KEY REFERENCES person(id) ON DELETE CASCADE,
    wiki_title TEXT NOT NULL,
    full_text TEXT NOT NULL
);

-- CBDB 人物映射（姓名消歧后的权威 id 与生卒籍贯）。
CREATE TABLE IF NOT EXISTS person_cbdb (
    person_id TEXT PRIMARY KEY REFERENCES person(id) ON DELETE CASCADE,
    cbdb_id INTEGER NOT NULL,
    index_year INTEGER,
    birthyear INTEGER,
    deathyear INTEGER,
    addr_chn TEXT
);

-- 《明史》传文索引：build_mingshi_corpus.py 建立的人物→卷次/选段映射。
CREATE TABLE IF NOT EXISTS person_mingshi (
    person_id TEXT NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    juan INTEGER NOT NULL,
    kind TEXT NOT NULL,
    excerpt TEXT NOT NULL,
    PRIMARY KEY(person_id, juan)
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

    if not DATABASE_PATH.exists() and all(
        (CONTENT_DIRECTORY / f"{table}.jsonl").exists() for table in CONTENT_TABLES
    ):
        import_content()
    with connect() as connection:
        connection.executescript(SCHEMA)
        _migrate_event_columns(connection)
        _migrate_institution_promotion_columns(connection)
        _migrate_person_columns(connection)
        _ensure_person_profile_taxonomy(connection)
        if connection.execute("PRAGMA user_version").fetchone()[0] == _catalog_digest():
            return
        _synchronize_catalog(connection)
        connection.execute(f"PRAGMA user_version = {_catalog_digest()}")


def _migrate_event_columns(connection: sqlite3.Connection) -> None:
    """Keep locally installed pre-metadata databases readable during an APK upgrade."""

    columns = {row[1] for row in connection.execute("PRAGMA table_info(event)")}
    if "end_year" not in columns:
        connection.execute("ALTER TABLE event ADD COLUMN end_year INTEGER NOT NULL DEFAULT 0")
    if "event_type" not in columns:
        connection.execute("ALTER TABLE event ADD COLUMN event_type TEXT NOT NULL DEFAULT '未分类'")
    connection.execute("UPDATE event SET end_year = year WHERE end_year = 0")


def _migrate_institution_promotion_columns(connection: sqlite3.Connection) -> None:
    """Add a route label without invalidating an installed content library."""

    columns = {row[1] for row in connection.execute("PRAGMA table_info(institution_promotion)")}
    if "track" not in columns:
        connection.execute(
            "ALTER TABLE institution_promotion ADD COLUMN track TEXT NOT NULL DEFAULT '常见任用路径'"
        )


def _catalog_digest() -> int:
    """种子名录指纹；catalog.py 改动后，下一次启动会重新回写一次。

    未改动时跳过回写：SQLite 即使写入相同的值也会脏化数据库文件，
    而 person_relation 的 AUTOINCREMENT 每次插入尝试还要预占 rowid。
    """

    payload = repr((SOURCE, REIGNS, PEOPLE, EVENTS, RELATIONS, INSTITUTIONS, SPECIAL_ITEMS, PORTRAIT_KEYS))
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:4], "big") & 0x7FFFFFFF


def _synchronize_catalog(connection: sqlite3.Connection) -> None:
    """Replay the packaged catalog over the content store."""

    source_id = SOURCE["id"]
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
    connection.executemany(
        """
        INSERT INTO special_item(id, name, category, era, description, position, source_id)
        VALUES (:id, :name, :category, :era, :description, :position, :source_id)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            category = excluded.category,
            era = excluded.era,
            description = excluded.description,
            position = excluded.position,
            source_id = excluded.source_id
        """,
        [{**item, "position": position, "source_id": source_id} for position, item in enumerate(SPECIAL_ITEMS)],
    )
    _apply_asset_metadata(connection)


def _migrate_person_columns(connection: sqlite3.Connection) -> None:
    """Apply additive SQLite migrations for databases created by earlier app versions."""

    columns = {row[1] for row in connection.execute("PRAGMA table_info(person)")}
    if "family_summary" not in columns:
        connection.execute("ALTER TABLE person ADD COLUMN family_summary TEXT NOT NULL DEFAULT ''")
    if "verification_status" not in columns:
        connection.execute("ALTER TABLE person ADD COLUMN verification_status TEXT NOT NULL DEFAULT '未校验'")
    if "display_name" not in columns:
        connection.execute("ALTER TABLE person ADD COLUMN display_name TEXT NOT NULL DEFAULT ''")
    if "archive_start_year" not in columns:
        connection.execute("ALTER TABLE person ADD COLUMN archive_start_year INTEGER NOT NULL DEFAULT 0")
    connection.execute("UPDATE person SET display_name = name WHERE trim(display_name) = ''")


def _ensure_person_profile_taxonomy(connection: sqlite3.Connection) -> None:
    """Seed the controlled categories and four visible profile sections for upgraded databases."""

    connection.executemany(
        """
        INSERT INTO person_category(id, label, position, description)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            label = excluded.label,
            position = excluded.position,
            description = excluded.description
        """,
        PERSON_CATEGORIES,
    )
    # “封爵”是爵位状态，不是人物职业或宫廷身份。升级旧库时先将该标签迁到
    # “宗藩”，再移除已废止的目录项；后续内容导入会按人物自身的来源证据细分。
    connection.execute("UPDATE person SET category = '宗藩' WHERE category = '封爵'")
    category_ids = ", ".join("?" for _ in PERSON_CATEGORIES)
    connection.execute(
        f"DELETE FROM person_category WHERE id NOT IN ({category_ids})",
        tuple(category[0] for category in PERSON_CATEGORIES),
    )
    connection.executemany(
        """
        INSERT INTO person_section_definition(section_key, title, position, description)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(section_key) DO UPDATE SET
            title = excluded.title,
            position = excluded.position,
            description = excluded.description
        """,
        PERSON_SECTION_DEFINITIONS,
    )


def _apply_asset_metadata(connection: sqlite3.Connection) -> None:
    """Synchronize metadata that is packaged with the Android client."""

    connection.executemany(
        "UPDATE person SET portrait_key = ? WHERE id = ?",
        [(key, person_id) for person_id, key in PORTRAIT_KEYS.items()],
    )


def export_content() -> list[tuple[str, int]]:
    """把内容库逐表导出为 JSONL，返回各表行数供调用方报告。"""

    CONTENT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    counts: list[tuple[str, int]] = []
    with connect() as connection:
        for table in CONTENT_TABLES:
            order = CONTENT_ORDER.get(table)
            rows = connection.execute(
                f"SELECT * FROM {table}" + (f" ORDER BY {', '.join(order)}" if order else "")
            ).fetchall()
            serialized_rows = []
            for row in rows:
                record = dict(row)
                # 总档时间只在确有跨年号档案归属时写入内容真相；其余人物走列默认值，
                # 避免一次新增排序字段让两千余条未改内容产生无意义的版本差异。
                if table == "person" and record.get("archive_start_year") == 0:
                    record.pop("archive_start_year")
                serialized_rows.append(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            payload = "".join(serialized_rows)
            (CONTENT_DIRECTORY / f"{table}.jsonl").write_text(payload, encoding="utf-8")
            counts.append((table, len(rows)))
    return counts


def import_content() -> list[tuple[str, int]]:
    """从 JSONL 重建内容库；旧库先备份为 .bak，避免文本不全时丢内容。"""

    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
    if DATABASE_PATH.exists():
        DATABASE_PATH.replace(DATABASE_PATH.with_name("ming_history.sqlite3.bak"))
    counts: list[tuple[str, int]] = []
    with connect() as connection:
        connection.executescript(SCHEMA)
        for table in CONTENT_TABLES:
            path = CONTENT_DIRECTORY / f"{table}.jsonl"
            if not path.exists():
                raise SystemExit(f"缺少 {path}；请先在内容完整的机器上执行 export。")
            records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if records:
                # 按各条记录自己的列插入：未提供的列走 schema 默认值，
                # 取全表列并集再补 None 会撞上 NOT NULL DEFAULT 的约束。
                grouped: dict[tuple[str, ...], list[dict]] = {}
                for record in records:
                    grouped.setdefault(tuple(sorted(record)), []).append(record)
                for columns, group in grouped.items():
                    connection.executemany(
                        f"INSERT INTO {table}({', '.join(columns)}) "
                        f"VALUES ({', '.join(':' + name for name in columns)})",
                        [{column: record[column] for column in columns} for record in group],
                    )
            connection.commit()
            counts.append((table, len(records)))
        connection.execute("UPDATE event SET end_year = year WHERE end_year = 0")
        # JSONL 是内容真相。新导入库若保留默认 user_version=0，会在首次服务启动时被
        # catalog.py 的旧种子字段回写，覆盖已审计的人物分类或介绍；写入当前指纹即可
        # 让启动同步仅在 catalog 本身变化时运行。
        connection.execute(f"PRAGMA user_version = {_catalog_digest()}")
    return counts
