
import os
import sqlite3
from datetime import date, datetime, timezone

from flask import Flask, g, jsonify, request
from flask_cors import CORS


# --------------------------------------------------
# App configuration
# --------------------------------------------------

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tasks.db"
)

VALID_PRIORITIES = {"low", "medium", "high"}

PRIORITY_RANK = {
    "high": 0,
    "medium": 1,
    "low": 2,
}


# --------------------------------------------------
# Database
# --------------------------------------------------

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

    columns = {
        row[1]
        for row in db.execute(
            "PRAGMA table_info(tasks)"
        ).fetchall()
    }

    if "priority" not in columns:
        db.execute(
            """
            ALTER TABLE tasks
            ADD COLUMN priority TEXT NOT NULL DEFAULT 'medium'
            """
        )

    if "category" not in columns:
        db.execute(
            """
            ALTER TABLE tasks
            ADD COLUMN category TEXT NOT NULL DEFAULT ''
            """
        )

    if "due_date" not in columns:
        db.execute(
            """
            ALTER TABLE tasks
            ADD COLUMN due_date TEXT
            """
        )

    db.commit()
    db.close()


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def row_to_task(row):
    due_date = row["due_date"]

    overdue = (
        bool(due_date)
        and not bool(row["done"])
        and due_date < date.today().isoformat()
    )

    return {
        "id": row["id"],
        "title": row["title"],
        "done": bool(row["done"]),
        "priority": row["priority"],
        "category": row["category"],
        "due_date": due_date,
        "overdue": overdue,
        "created_at": row["created_at"],
    }


def parse_due_date(value):
    if value in (None, ""):
        return None

    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValueError(
            "due_date must be in YYYY-MM-DD format"
        )

    return value


# --------------------------------------------------
# Home / health check
# --------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "ok",
        "message": "Todo API is running"
    })


# --------------------------------------------------
# Get all tasks
# --------------------------------------------------

@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    db = get_db()

    rows = db.execute(
        "SELECT * FROM tasks"
    ).fetchall()

    tasks = [
        row_to_task(row)
        for row in rows
    ]

    # Search
    q = request.args.get(
        "q",
        ""
    ).strip().lower()

    if q:
        tasks = [
            task
            for task in tasks
            if q in task["title"].lower()
        ]

    # Category
    category = request.args.get(
        "category",
        ""
    ).strip()

    if category:
        tasks = [
            task
            for task in tasks
            if task["category"] == category
        ]

    # Status
    status = request.args.get(
        "status",
        ""
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

    # Sorting
    sort = request.args.get(
        "sort",
        "created"
    )

    if sort == "priority":
        tasks.sort(
            key=lambda task:
            PRIORITY_RANK.get(
                task["priority"],
                1
            )
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
            key=lambda task: task["id"],
            reverse=True
        )

    return jsonify(tasks)


# --------------------------------------------------
# Create task
# --------------------------------------------------

@app.route("/api/tasks", methods=["POST"])
def create_task():
    data = request.get_json(
        silent=True
    ) or {}

    title = (
        data.get("title") or ""
    ).strip()

    if not title:
        return jsonify({
            "error": "title is required"
        }), 400

    priority = data.get(
        "priority",
        "medium"
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
    except ValueError as error:
        return jsonify({
            "error": str(error)
        }), 400

    db = get_db()

    cursor = db.execute(
        """
        INSERT INTO tasks (
            title,
            done,
            priority,
            category,
            due_date,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            title,
            0,
            priority,
            category,
            due_date,
            datetime.now(
                timezone.utc
            ).isoformat(),
        )
    )

    db.commit()

    row = db.execute(
        """
        SELECT *
        FROM tasks
        WHERE id = ?
        """,
        (cursor.lastrowid,)
    ).fetchone()

    return jsonify(
        row_to_task(row)
    ), 201


# --------------------------------------------------
# Update task
# --------------------------------------------------

@app.route(
    "/api/tasks/<int:task_id>",
    methods=["PATCH"]
)
def update_task(task_id):
    data = request.get_json(
        silent=True
    ) or {}

    db = get_db()

    row = db.execute(
        """
        SELECT *
        FROM tasks
        WHERE id = ?
        """,
        (task_id,)
    ).fetchone()

    if row is None:
        return jsonify({
            "error": "task not found"
        }), 404

    title = data.get(
        "title",
        row["title"]
    )

    title = (
        title or ""
    ).strip()

    if not title:
        return jsonify({
            "error": "title is required"
        }), 400

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

    category = (
        category or ""
    ).strip()

    if "due_date" in data:
        try:
            due_date = parse_due_date(
                data.get("due_date")
            )
        except ValueError as error:
            return jsonify({
                "error": str(error)
            }), 400
    else:
        due_date = row["due_date"]

    db.execute(
        """
        UPDATE tasks
        SET
            title = ?,
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
        )
    )

    db.commit()

    updated_row = db.execute(
        """
        SELECT *
        FROM tasks
        WHERE id = ?
        """,
        (task_id,)
    ).fetchone()

    return jsonify(
        row_to_task(updated_row)
    )


# --------------------------------------------------
# Delete task
# --------------------------------------------------

@app.route(
    "/api/tasks/<int:task_id>",
    methods=["DELETE"]
)
def delete_task(task_id):
    db = get_db()

    row = db.execute(
        """
        SELECT *
        FROM tasks
        WHERE id = ?
        """,
        (task_id,)
    ).fetchone()

    if row is None:
        return jsonify({
            "error": "task not found"
        }), 404

    db.execute(
        """
        DELETE FROM tasks
        WHERE id = ?
        """,
        (task_id,)
    )

    db.commit()

    return "", 204


# --------------------------------------------------
# Categories
# --------------------------------------------------

@app.route("/api/categories", methods=["GET"])
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

    return jsonify([
        row["category"]
        for row in rows
    ])


# --------------------------------------------------
# Initialize database
# --------------------------------------------------

init_db()


# --------------------------------------------------
# Local development
# --------------------------------------------------

if __name__ == "__main__":
    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )

