import json
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta


def data_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DB_PATH = os.path.join(data_dir(), "pomodoro_data.db")
DEFAULT_PROJECT_ID = 1
DEFAULT_SETTINGS = {
    "work_minutes": "25",
    "short_minutes": "5",
    "long_minutes": "15",
    "long_every": "4",
    "sound_effect": "chime",
    "ui_theme": "dark",
}

STATUS_TODO = 0
STATUS_DOING = 1
STATUS_DONE = 2
STATUS_NAMES = {STATUS_TODO: "待办", STATUS_DOING: "进行中", STATUS_DONE: "已完成"}

PRIORITY_LOW = 0
PRIORITY_MED = 1
PRIORITY_HIGH = 2
PRIORITY_NAMES = {PRIORITY_LOW: "低", PRIORITY_MED: "中", PRIORITY_HIGH: "高"}


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def datetime_now():
    return datetime.now().isoformat(timespec="seconds")


def init_db():
    with _conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS records ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "start_time TEXT NOT NULL,"
            "end_time TEXT,"
            "planned_minutes INTEGER,"
            "completed INTEGER DEFAULT 0,"
            "mode TEXT DEFAULT 'countdown',"
            "project_id INTEGER DEFAULT 1)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS projects ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "name TEXT NOT NULL UNIQUE,"
            "created_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS sections ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "project_id INTEGER NOT NULL,"
            "name TEXT NOT NULL,"
            "sort_order INTEGER DEFAULT 0)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS cards ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "section_id INTEGER NOT NULL,"
            "title TEXT NOT NULL,"
            "note TEXT DEFAULT '',"
            "status INTEGER DEFAULT 0,"
            "priority INTEGER DEFAULT 1,"
            "created_at TEXT,"
            "updated_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS items ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "card_id INTEGER NOT NULL,"
            "content TEXT NOT NULL,"
            "note TEXT DEFAULT '',"
            "status INTEGER DEFAULT 0,"
            "priority INTEGER DEFAULT 1,"
            "created_at TEXT,"
            "done_at TEXT)"
        )
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        conn.execute(
            "INSERT OR IGNORE INTO projects (id, name, created_at) VALUES (1, '默认', ?)",
            (datetime_now(),),
        )
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(records)")]
        if "mode" not in columns:
            conn.execute("ALTER TABLE records ADD COLUMN mode TEXT DEFAULT 'countdown'")
        if "project_id" not in columns:
            conn.execute(
                "ALTER TABLE records ADD COLUMN project_id INTEGER DEFAULT 1"
            )
        conn.execute("UPDATE records SET project_id = 1 WHERE project_id IS NULL")

        card_columns = [row["name"] for row in conn.execute("PRAGMA table_info(cards)")]
        if "priority" not in card_columns:
            conn.execute(
                "ALTER TABLE cards ADD COLUMN priority INTEGER DEFAULT 1"
            )
        if "done_at" not in card_columns:
            conn.execute("ALTER TABLE cards ADD COLUMN done_at TEXT")
        if "tags" not in card_columns:
            conn.execute("ALTER TABLE cards ADD COLUMN tags TEXT DEFAULT '[]'")


def get_settings():
    with _conn() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: row["value"] for row in rows}


def save_settings(settings):
    with _conn() as conn:
        for key, value in settings.items():
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value)),
            )


def list_projects():
    with _conn() as conn:
        return conn.execute("SELECT * FROM projects ORDER BY id").fetchall()


def create_project(name):
    with _conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO projects (name, created_at) VALUES (?, ?)",
                (name, datetime_now()),
            )
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None


def delete_project(project_id):
    if project_id == DEFAULT_PROJECT_ID:
        return False
    with _conn() as conn:
        conn.execute(
            "DELETE FROM items WHERE card_id IN ("
            "SELECT id FROM cards WHERE section_id IN ("
            "SELECT id FROM sections WHERE project_id = ?))",
            (project_id,),
        )
        conn.execute(
            "DELETE FROM cards WHERE section_id IN ("
            "SELECT id FROM sections WHERE project_id = ?)",
            (project_id,),
        )
        conn.execute("DELETE FROM sections WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.execute(
            "UPDATE records SET project_id = ? WHERE project_id = ?",
            (DEFAULT_PROJECT_ID, project_id),
        )
    return True


def start_record(planned_minutes, mode="countdown", project_id=DEFAULT_PROJECT_ID):
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO records (start_time, planned_minutes, completed, mode, project_id) "
            "VALUES (?, ?, 0, ?, ?)",
            (datetime_now(), planned_minutes, mode, project_id),
        )
        return cur.lastrowid


def complete_record(record_id):
    with _conn() as conn:
        conn.execute(
            "UPDATE records SET completed = 1, end_time = ? WHERE id = ?",
            (datetime_now(), record_id),
        )


def finish_record(record_id):
    with _conn() as conn:
        conn.execute(
            "UPDATE records SET end_time = ? WHERE id = ?",
            (datetime_now(), record_id),
        )


def _project_clause(project_id):
    if project_id is None:
        return "", ()
    return "AND project_id = ?", (project_id,)


def _minutes_expr():
    return (
        "ROUND(CASE WHEN mode = 'stopwatch' "
        "THEN (julianday(end_time) - julianday(start_time)) * 1440 "
        "ELSE planned_minutes END)"
    )


def counts_since(days, project_id=None):
    start = date.today() - timedelta(days=days - 1)
    clause, params = _project_clause(project_id)
    with _conn() as conn:
        rows = conn.execute(
            "SELECT substr(start_time, 1, 10) AS d, COUNT(*) AS n "
            "FROM records WHERE completed = 1 AND substr(start_time, 1, 10) >= ? "
            + clause + " GROUP BY d",
            (start.isoformat(),) + params,
        ).fetchall()
    count_map = {row["d"]: row["n"] for row in rows}
    out = []
    for i in range(days):
        day = start + timedelta(days=i)
        out.append((day.isoformat(), count_map.get(day.isoformat(), 0)))
    return out


def minutes_since(days, project_id=None):
    """Return completed focus minutes grouped by day for chart views."""
    start = date.today() - timedelta(days=days - 1)
    clause, params = _project_clause(project_id)
    with _conn() as conn:
        rows = conn.execute(
            "SELECT substr(start_time, 1, 10) AS d, "
            "COALESCE(SUM(" + _minutes_expr() + "), 0) AS minutes "
            "FROM records WHERE completed = 1 AND substr(start_time, 1, 10) >= ? "
            + clause + " GROUP BY d",
            (start.isoformat(),) + params,
        ).fetchall()
    minute_map = {row["d"]: row["minutes"] for row in rows}
    return [
        ((start + timedelta(days=i)).isoformat(), minute_map.get((start + timedelta(days=i)).isoformat(), 0))
        for i in range(days)
    ]


def summary(days, project_id=None):
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    clause, params = _project_clause(project_id)
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(" + _minutes_expr() + "), 0) AS m "
            "FROM records WHERE completed = 1 AND substr(start_time, 1, 10) >= ? "
            + clause,
            (start,) + params,
        ).fetchone()
        started = conn.execute(
            "SELECT COUNT(*) FROM records WHERE substr(start_time, 1, 10) >= ? "
            + clause,
            (start,) + params,
        ).fetchone()[0]
    return {"count": row["n"], "minutes": row["m"], "started": started}


def summary_total(project_id=None):
    clause, params = _project_clause(project_id)
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(" + _minutes_expr() + "), 0) AS m "
            "FROM records WHERE completed = 1 " + clause,
            params,
        ).fetchone()
    return {"count": row["n"], "minutes": row["m"]}


def recent(limit=20, project_id=None):
    clause, params = _project_clause(project_id)
    clause = clause.replace("project_id", "r.project_id")
    with _conn() as conn:
        return conn.execute(
            "SELECT r.*, p.name AS project_name, "
            "CAST(ROUND(CASE WHEN r.mode = 'stopwatch' "
            "THEN (julianday(r.end_time) - julianday(r.start_time)) * 1440 "
            "ELSE r.planned_minutes END) AS INTEGER) AS minutes "
            "FROM records r LEFT JOIN projects p ON p.id = r.project_id "
            "WHERE 1=1 " + clause + " ORDER BY r.id DESC LIMIT ?",
            params + (limit,),
        ).fetchall()


def list_sections(project_id):
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM sections WHERE project_id = ? "
            "ORDER BY sort_order, id",
            (project_id,),
        ).fetchall()


def add_section(project_id, name):
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO sections (project_id, name) VALUES (?, ?)",
            (project_id, name),
        )
        return cur.lastrowid


def rename_section(section_id, name):
    with _conn() as conn:
        conn.execute("UPDATE sections SET name = ? WHERE id = ?", (name, section_id))


def delete_section(section_id):
    with _conn() as conn:
        conn.execute(
            "DELETE FROM items WHERE card_id IN "
            "(SELECT id FROM cards WHERE section_id = ?)",
            (section_id,),
        )
        conn.execute("DELETE FROM cards WHERE section_id = ?", (section_id,))
        conn.execute("DELETE FROM sections WHERE id = ?", (section_id,))


def normalize_tags(tags):
    if isinstance(tags, str):
        tags = tags.replace("，", ",").split(",")
    result, seen = [], set()
    for tag in tags or []:
        tag = str(tag).strip().lstrip("#").strip()
        if tag and tag.casefold() not in seen:
            result.append(tag)
            seen.add(tag.casefold())
    return result


def card_tags(card):
    return json.loads(card["tags"] or "[]")


def list_tags(project_id=None):
    return sorted({tag for card in list_cards(project_id) for tag in card_tags(card)}, key=str.casefold)


def list_cards(project_id, search="", priority=None, tag=None, sort="priority"):
    with _conn() as conn:
        cards = conn.execute(
            "SELECT c.*, s.name AS section_name, p.name AS project_name, s.project_id, "
            "COUNT(i.id) AS total, "
            "COALESCE(SUM(CASE WHEN i.status = ? THEN 1 ELSE 0 END), 0) AS done "
            "FROM cards c "
            "JOIN sections s ON s.id = c.section_id "
            "JOIN projects p ON p.id = s.project_id "
            "LEFT JOIN items i ON i.card_id = c.id "
            "WHERE (? IS NULL OR s.project_id = ?) "
            "GROUP BY c.id ORDER BY c.priority DESC, s.sort_order, c.id",
            (STATUS_DONE, project_id, project_id),
        ).fetchall()
    query = search.strip().casefold()
    cards = [c for c in cards
             if (priority is None or c["priority"] == priority)
             and (not tag or tag.casefold() in [t.casefold() for t in card_tags(c)])
             and (not query or query in " ".join(
                 [c["title"], c["note"], c["section_name"], c["project_name"]] + card_tags(c)
             ).casefold())]
    if sort == "title":
        cards.sort(key=lambda c: (c["title"].casefold(), c["id"]))
    elif sort in ("created", "updated", "completed"):
        field = {"created": "created_at", "updated": "updated_at", "completed": "done_at"}[sort]
        cards.sort(key=lambda c: (c[field] or "", c["id"]), reverse=True)
    return cards


def add_card(section_id, title, note="", priority=PRIORITY_MED, tags=None, status=STATUS_TODO):
    if status not in STATUS_NAMES:
        raise ValueError("无效任务状态")
    now = datetime_now()
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO cards (section_id, title, note, status, priority, created_at, updated_at, tags, done_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (section_id, title, note, status, priority, now, now,
             json.dumps(normalize_tags(tags), ensure_ascii=False), now if status == STATUS_DONE else None),
        )
        return cur.lastrowid


def update_card(card_id, title=None, note=None, priority=None, tags=None, section_id=None):
    updates = []
    params = []
    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if note is not None:
        updates.append("note = ?")
        params.append(note)
    if priority is not None:
        updates.append("priority = ?")
        params.append(priority)
    if tags is not None:
        updates.append("tags = ?")
        params.append(json.dumps(normalize_tags(tags), ensure_ascii=False))
    if section_id is not None:
        updates.append("section_id = ?")
        params.append(section_id)
    if not updates:
        return
    updates.append("updated_at = ?")
    params.append(datetime_now())
    params.append(card_id)
    with _conn() as conn:
        conn.execute(
            "UPDATE cards SET " + ", ".join(updates) + " WHERE id = ?",
            params,
        )


def set_card_status(card_id, status):
    if status not in STATUS_NAMES:
        raise ValueError("无效任务状态")
    now = datetime_now()
    with _conn() as conn:
        conn.execute(
            "UPDATE cards SET done_at = CASE "
            "WHEN ? = 2 AND status <> 2 THEN ? "
            "WHEN ? = 2 THEN done_at ELSE NULL END, "
            "status = ?, updated_at = ? WHERE id = ?",
            (status, now, status, status, now, card_id),
        )


def delete_card(card_id):
    with _conn() as conn:
        conn.execute("DELETE FROM items WHERE card_id = ?", (card_id,))
        conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))


def card_progress(card_id):
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total, "
            "COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS done "
            "FROM items WHERE card_id = ?",
            (STATUS_DONE, card_id),
        ).fetchone()
    return (row["total"], row["done"])


def list_items(card_id):
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM items WHERE card_id = ? "
            "ORDER BY status, id",
            (card_id,),
        ).fetchall()


def add_item(card_id, content, note="", priority=PRIORITY_MED):
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO items (card_id, content, note, status, priority, created_at) "
            "VALUES (?, ?, ?, 0, ?, ?)",
            (card_id, content, note, priority, datetime_now()),
        )
        return cur.lastrowid


def set_item_status(item_id, status):
    with _conn() as conn:
        conn.execute(
            "UPDATE items SET status = ?, done_at = ? WHERE id = ?",
            (status, datetime_now() if status == STATUS_DONE else None, item_id),
        )


def set_item_priority(item_id, priority):
    with _conn() as conn:
        conn.execute("UPDATE items SET priority = ? WHERE id = ?", (priority, item_id))


def delete_item(item_id):
    with _conn() as conn:
        conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
