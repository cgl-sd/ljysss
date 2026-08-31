"""HTTP API for the 两京一十三省 historical content service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.gzip import GZipMiddleware

from .database import DATABASE_PATH, connect, initialize_database
@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="两京一十三省内容 API",
    version="0.1.0",
    description="人物、事件、关系、机构与史料来源的本地内容服务。",
    lifespan=lifespan,
)
# bootstrap 全量资料约 2MB 文本，gzip 后约 0.4MB；客户端以 Accept-Encoding 声明。
app.add_middleware(GZipMiddleware, minimum_size=1024)


def records(query: str, parameters: tuple = ()) -> list[dict]:
    with connect() as connection:
        return [dict(row) for row in connection.execute(query, parameters).fetchall()]


def record(query: str, parameters: tuple = ()) -> Optional[dict]:
    with connect() as connection:
        row = connection.execute(query, parameters).fetchone()
    return dict(row) if row else None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "database": DATABASE_PATH.name}


@app.get("/v1/reigns")
def list_reigns() -> list[dict]:
    return records(
        """
        SELECT r.*, COUNT(e.id) AS event_count
        FROM reign AS r
        LEFT JOIN event AS e ON e.reign_id = r.id
        GROUP BY r.id
        ORDER BY r.start_year
        """
    )


@app.get("/v1/bootstrap")
def bootstrap_content() -> dict:
    """A single content payload for development tools and consistency checks.

    全量内容一次下发（gzip 压缩传输）；App 一次加载后全内存访问，
    不再产生按需请求，这是当前规模下最高效的访问路径。
    """

    sections_by_person: dict[str, list[dict]] = {}
    for row in records(
        """
        SELECT person_id, section_key, title, position, content
        FROM person_section
        ORDER BY person_id, position
        """
    ):
        sections_by_person.setdefault(row["person_id"], []).append(row)
    people = list_people(category=None, q=None)
    for person in people:
        person["sections"] = sections_by_person.get(person["id"], [])
    return {
        "reigns": list_reigns(),
        "events": list_events(reign=None, year=None, q=None),
        "people": people,
        "person_categories": list_person_categories(),
        "person_section_definitions": list_person_section_definitions(),
        "relationships": list_relationships(),
        "institutions": list_institutions(),
        "specials": list_specials(),
    }


@app.get("/v1/events")
def list_events(
    reign: Optional[str] = None,
    year: Optional[int] = Query(default=None, ge=1368, le=1662),
    q: Optional[str] = None,
) -> list[dict]:
    conditions: list[str] = []
    parameters: list[object] = []
    if reign:
        conditions.append("e.reign_id = ?")
        parameters.append(reign)
    if year:
        conditions.append("e.year = ?")
        parameters.append(year)
    if q:
        conditions.append("(e.title LIKE ? OR e.summary LIKE ? OR e.place LIKE ?)")
        parameters.extend([f"%{q}%"] * 3)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    events = records(
        f"""
        SELECT e.*, r.title AS reign_title, s.title AS source_title
        FROM event AS e
        JOIN reign AS r ON r.id = e.reign_id
        JOIN source AS s ON s.id = e.source_id
        {where}
        ORDER BY e.year, e.id
        """,
        tuple(parameters),
    )
    for event in events:
        event["sections"] = records(
            """
            SELECT section_key, title, content, position
            FROM event_section
            WHERE event_id = ?
            ORDER BY position
            """,
            (event["id"],),
        )
        event["people"] = event_people(event["id"])
    return events


@app.get("/v1/events/{event_id}")
def get_event(event_id: str) -> dict:
    item = record(
        """
        SELECT e.*, r.title AS reign_title, s.title AS source_title, s.citation
        FROM event AS e
        JOIN reign AS r ON r.id = e.reign_id
        JOIN source AS s ON s.id = e.source_id
        WHERE e.id = ?
        """,
        (event_id,),
    )
    if not item:
        raise HTTPException(status_code=404, detail="未找到该事件")
    source = record(
        """
        SELECT locator
        FROM content_reference
        WHERE content_type = 'event' AND content_id = ? AND section_key = 'source'
        ORDER BY position
        LIMIT 1
        """,
        (event_id,),
    )
    item["source_locator"] = source["locator"] if source else ""
    item["sections"] = get_event_sections(event_id)
    item["people"] = event_people(event_id)
    return item


@app.get("/v1/people")
def list_people(
    category: Optional[str] = None,
    q: Optional[str] = None,
) -> list[dict]:
    conditions: list[str] = []
    parameters: list[object] = []
    if category:
        conditions.append("p.category = ?")
        parameters.append(category)
    if q:
        conditions.append("(p.name LIKE ? OR p.title LIKE ? OR p.reign LIKE ? OR p.courtesy_name LIKE ?)")
        parameters.extend([f"%{q}%"] * 4)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return records(
        f"""
        SELECT p.*, s.title AS source_title
        FROM person AS p
        JOIN source AS s ON s.id = p.source_id
        {where}
        ORDER BY p.reign, p.name
        """,
        tuple(parameters),
    )


@app.get("/v1/person-categories")
def list_person_categories() -> list[dict]:
    """Return the registered six-way taxonomy together with its current person counts."""

    return records(
        """
        SELECT c.id, c.label, c.position, c.description, COUNT(p.id) AS person_count
        FROM person_category AS c
        LEFT JOIN person AS p ON p.category = c.label
        GROUP BY c.id, c.label, c.position, c.description
        ORDER BY c.position
        """
    )


@app.get("/v1/person-profile-schema")
def person_profile_schema() -> dict:
    """Expose the classification registry and the only four allowed detail sections."""

    return {
        "categories": list_person_categories(),
        "sections": list_person_section_definitions(),
    }


def list_person_section_definitions() -> list[dict]:
    return records(
        """
        SELECT section_key, title, position, description
        FROM person_section_definition
        ORDER BY position
        """
    )


@app.get("/v1/people/{person_id}")
def get_person(person_id: str) -> dict:
    person = record(
        """
        SELECT p.*, s.title AS source_title, s.citation
        FROM person AS p
        JOIN source AS s ON s.id = p.source_id
        WHERE p.id = ?
        """,
        (person_id,),
    )
    if not person:
        raise HTTPException(status_code=404, detail="未找到该人物")

    person["sections"] = records(
        """
        SELECT section_key, title, position, content
        FROM person_section
        -- 相关事件只从 event_participant 这张正式关系表提供；历史自动抽取的
        -- person_section.events 不向 API 暴露，避免客户端误将编年残句当作关联。
        WHERE person_id = ? AND section_key <> 'events'
        ORDER BY position
        """,
        (person_id,),
    )

    person["relationships"] = records(
        """
        SELECT pr.*, fp.name AS from_name, tp.name AS to_name
        FROM person_relation AS pr
        JOIN person AS fp ON fp.id = pr.from_person_id
        JOIN person AS tp ON tp.id = pr.to_person_id
        WHERE pr.from_person_id = ? OR pr.to_person_id = ?
        ORDER BY pr.reign, pr.id
        """,
        (person_id, person_id),
    )
    person["events"] = records(
        """
        SELECT e.id, e.year, e.month, e.title, e.summary, e.place, ep.role
        FROM event_participant AS ep
        JOIN event AS e ON e.id = ep.event_id
        WHERE ep.person_id = ?
        ORDER BY e.year, e.id
        """,
        (person_id,),
    )
    return person


def event_people(event_id: str) -> list[dict]:
    """Formal event participants.  The same table drives both event and person links."""

    return records(
        """
        SELECT p.id, p.name, p.display_name, p.title, ep.role
        FROM event_participant AS ep
        JOIN person AS p ON p.id = ep.person_id
        WHERE ep.event_id = ?
        ORDER BY ep.rowid
        """,
        (event_id,),
    )


@app.get("/v1/events/{event_id}/sections")
def get_event_sections(event_id: str) -> list[dict]:
    if not record("SELECT id FROM event WHERE id = ?", (event_id,)):
        raise HTTPException(status_code=404, detail="未找到该事件")
    return records(
        """
        SELECT section_key, title, content
        FROM event_section
        WHERE event_id = ?
        ORDER BY position
        """,
        (event_id,),
    )


@app.get("/v1/relationships")
def list_relationships() -> list[dict]:
    return records(
        """
        SELECT pr.*, fp.name AS from_name, tp.name AS to_name, s.title AS source_title
        FROM person_relation AS pr
        JOIN person AS fp ON fp.id = pr.from_person_id
        JOIN person AS tp ON tp.id = pr.to_person_id
        JOIN source AS s ON s.id = pr.source_id
        ORDER BY pr.reign, pr.id
        """
    )


@app.get("/v1/institutions")
def list_institutions() -> list[dict]:
    institutions = records(
        """
        SELECT i.*, s.title AS source_title
        FROM institution AS i
        JOIN source AS s ON s.id = i.source_id
        ORDER BY i.category, i.id
        """
    )
    for institution in institutions:
        promotion_rows = records(
            "SELECT track, label FROM institution_promotion WHERE institution_id = ? ORDER BY position",
            (institution["id"],),
        )
        promotion_tracks: dict[str, list[str]] = {}
        for entry in promotion_rows:
            promotion_tracks.setdefault(entry["track"], []).append(entry["label"])
        institution["promotion_tracks"] = [
            {"title": title, "steps": steps}
            for title, steps in promotion_tracks.items()
        ]
        # Keep the original flat field available to existing development tools.
        institution["promotion_path"] = [entry["label"] for entry in promotion_rows]
        institution["reforms"] = records(
            """
            SELECT year, title, description
            FROM institution_reform
            WHERE institution_id = ?
            ORDER BY position
            """,
            (institution["id"],),
        )
        institution["sections"] = records(
            """
            SELECT section_key, title, content, position
            FROM institution_section
            WHERE institution_id = ?
            ORDER BY position
            """,
            (institution["id"],),
        )
        institution["people"] = records(
            """
            SELECT p.id, p.name, p.title, ip.role
            FROM institution_person AS ip
            JOIN person AS p ON p.id = ip.person_id
            WHERE ip.institution_id = ?
            ORDER BY ip.position
            """,
            (institution["id"],),
        )
    return institutions


@app.get("/v1/specials")
def list_specials() -> list[dict]:
    """天下页“典章”科普：宫殿、器物与制度名物。"""

    specials = records("SELECT id, name, category, era, description FROM special_item ORDER BY position")
    for special in specials:
        special["sections"] = records(
            """
            SELECT section_key, title, content, position
            FROM special_section
            WHERE special_item_id = ?
            ORDER BY position
            """,
            (special["id"],),
        )
        special["people"] = records(
            """
            SELECT p.id, p.name, p.title, sp.role
            FROM special_person AS sp
            JOIN person AS p ON p.id = sp.person_id
            WHERE sp.special_item_id = ?
            ORDER BY sp.position
            """,
            (special["id"],),
        )
    return specials


@app.get("/v1/sources/{source_id}")
def get_source(source_id: str) -> dict:
    source = record("SELECT * FROM source WHERE id = ?", (source_id,))
    if not source:
        raise HTTPException(status_code=404, detail="未找到该史料来源")
    # 编辑阶段的内部标记不属于用户端资料内容。
    source.pop("review_status", None)
    return source
