import os
import sqlite3
from datetime import date, datetime, timezone

from flask import Flask, g, jsonify, request
from flask_cors import CORS


DB_PATH = os.path.join(os.path.dirname(__file__), "tasks.db")

app = Flask(__name__)
CORS(app)

VALID_PRIORITIES = {"low", "medium", "high"}
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            priority TEXT NOT NULL DEFAULT 'medium',
            category TEXT NOT NULL DEFAULT '',
            due_date TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    db.commit()

    cols = [
        row[1]
        for row in db.execute("PRAGMA table_info(tasks)")
    ]

    if "priority" not in cols:
        db.execute(
            "ALTER TABLE tasks ADD COLUMN priority TEXT NOT NULL DEFAULT 'medium'"
        )

    if "category" not in cols:
        db.execute(
            "ALTER TABLE tasks ADD COLUMN category TEXT NOT NULL DEFAULT ''"
        )

    if "due_date" not in cols:
        db.execute(
            "ALTER TABLE tasks ADD COLUMN due_date TEXT"
        )

    db.commit()
    db.close()


def row_to_task(row):
    due = row["due_date"]

    overdue = (
        bool(due)
        and not bool(row["done"])
        and due < date.today().isoformat()
    )

    return {
        "id": row["id"],
        "title": row["title"],
        "done": bool(row["done"]),
        "priority": row["priority"],
        "category": row["category"],
        "due_date": due,
        "overdue": overdue,
        "created_at": row["created_at"],
    }


def parse_due_date(value):
    """Return a validated YYYY-MM-DD string, or None."""

    if value in (None, ""):
        return None

    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValueError(
            "due_date must be in YYYY-MM-DD format"
        )

    return value


@app.get("/api/tasks")
def list_tasks():
    db = get_db()

    rows = db.execute(
        "SELECT * FROM tasks"
    ).fetchall()

    tasks = [row_to_task(row) for row in rows]

    q = request.args.get("q", "").strip().lower()

    if q:
        tasks = [
            task
            for task in tasks
            if q in task["title"].lower()
        ]

    category = request.args.get(
        "category", ""
    ).strip()

    if category:
        tasks = [
            task
            for task in tasks
            if task["category"] == category
        ]

    status = request.args.get(
        "status", ""
    ).strip()

    if status == "open":
        tasks = [
            task
            for task in tasks
            if not task["done"]
        ]

    elif status == "done":
        tasks = [
            task
            for task in tasks
            if task["done"]
        ]

    sort = request.args.get(
        "sort", "created"
    )

    if sort == "priority":
        tasks.sort(
            key=lambda task:
            PRIORITY_RANK[task["priority"]]
        )

    elif sort == "due_date":
        tasks.sort(
            key=lambda task: (
                task["due_date"] is None,
                task["due_date"] or ""
            )
        )

    elif sort == "title":
        tasks.sort(
            key=lambda task:
            task["title"].lower()
        )

    else:
        tasks.sort(
            key=lambda task:
            task["id"],
            reverse=True
        )

    return jsonify(tasks)


@app.get("/api/categories")
def list_categories():
    db = get_db()

    rows = db.execute(
        """
        SELECT DISTINCT category
        FROM tasks
        WHERE category != ''
        ORDER BY category
        """
    ).fetchall()

    return jsonify(
        [row["category"] for row in rows]
    )


@app.post("/api/tasks")
def create_task():
    data = request.get_json(silent=True) or {}

    title = (data.get("title") or "").strip()

    if not title:
        return jsonify(
            {"error": "title is required"}
        ), 400

    priority = data.get(
        "priority", "medium"
    )

    if priority not in VALID_PRIORITIES:
        return jsonify({
            "error":
            "priority must be one of low, medium, high"
        }), 400

    category = (
        data.get("category") or ""
    ).strip()

    try:
        due_date = parse_due_date(
            data.get("due_date")
        )
    except ValueError as e:
        return jsonify(
            {"error": str(e)}
        ), 400

    db = get_db()

    cur = db.execute(
        """
        INSERT INTO tasks
        (title, done, priority, category, due_date, created_at)
        VALUES (?, 0, ?, ?, ?, ?)
        """,
        (
            title,
            priority,
            category,
            due_date,
            datetime.now(timezone.utc).isoformat(),
        ),
    )

    db.commit()

    row = db.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()

    return jsonify(
        row_to_task(row)
    ), 201


@app.patch("/api/tasks/<int:task_id>")
def update_task(task_id):
    data = request.get_json(
        silent=True
    ) or {}

    db = get_db()

    row = db.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()

    if row is None:
        return jsonify({
            "error": "task not found"
        }), 404

    title = data.get(
        "title", row["title"]
    )

    done = data.get(
        "done",
        bool(row["done"])
    )

    priority = data.get(
        "priority",
        row["priority"]
    )

    if priority not in VALID_PRIORITIES:
        return jsonify({
            "error":
            "priority must be one of low, medium, high"
        }), 400

    category = data.get(
        "category",
        row["category"]
    )

    if "due_date" in data:
        try:
            due_date = parse_due_date(
                data.get("due_date")
            )
        except ValueError as e:
            return jsonify(
                {"error": str(e)}
            ), 400
    else:
        due_date = row["due_date"]

    db.execute(
        """
        UPDATE tasks
        SET title = ?,
            done = ?,
            priority = ?,
            category = ?,
            due_date = ?
        WHERE id = ?
        """,
        (
            title,
            1 if done else 0,
            priority,
            category,
            due_date,
            task_id,
        ),
    )

    db.commit()

    row = db.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()

    return jsonify(
        row_to_task(row)
    )


@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id):
    db = get_db()

    row = db.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()

    if row is None:
        return jsonify({
            "error": "task not found"
        }), 404

    db.execute(
        "DELETE FROM tasks WHERE id = ?",
        (task_id,),
    )

    db.commit()

    return "", 204


if __name__ == "__main__":
    init_db()

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get("PORT", 5000)
        ),
        debug=False,
    )