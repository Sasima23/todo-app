import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API = "/api/tasks";

const PRIORITY_LABEL = { high: "High", medium: "Med", low: "Low" };

function Check({ done }) {
  return (
    <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
      <rect
        x="1.5"
        y="1.5"
        width="17"
        height="17"
        rx="2"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
      />
      {done && (
        <path
          d="M4.5 10.2 L8.2 14 L15.5 5.8"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
    </svg>
  );
}

function formatDue(dateStr) {
  if (!dateStr) return null;
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function App() {
  const [tasks, setTasks] = useState([]);
  const [categories, setCategories] = useState([]);

  const [draft, setDraft] = useState("");
  const [draftPriority, setDraftPriority] = useState("medium");
  const [draftCategory, setDraftCategory] = useState("");
  const [draftDue, setDraftDue] = useState("");

  const [filter, setFilter] = useState("open");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [sort, setSort] = useState("created");

  const [dark, setDark] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchTasks();
    fetchCategories();
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  async function fetchTasks() {
    try {
      setLoading(true);
      const res = await fetch(API);
      if (!res.ok) throw new Error("Could not load the ledger.");
      setTasks(await res.json());
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function fetchCategories() {
    try {
      const res = await fetch("/api/categories");
      if (res.ok) setCategories(await res.json());
    } catch {
      // non-critical; ignore
    }
  }

  async function addTask(e) {
    e.preventDefault();
    const title = draft.trim();
    if (!title) return;
    setDraft("");
    try {
      const res = await fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          priority: draftPriority,
          category: draftCategory.trim(),
          due_date: draftDue || null,
        }),
      });
      if (!res.ok) throw new Error("Could not add the entry.");
      const created = await res.json();
      setTasks((prev) => [created, ...prev]);
      setDraftDue("");
      if (draftCategory.trim() && !categories.includes(draftCategory.trim())) {
        setCategories((prev) => [...prev, draftCategory.trim()].sort());
      }
    } catch (e) {
      setError(e.message);
    }
  }

  async function toggleTask(task) {
    setTasks((prev) =>
      prev.map((t) => (t.id === task.id ? { ...t, done: !t.done } : t))
    );
    try {
      const res = await fetch(`${API}/${task.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ done: !task.done }),
      });
      if (!res.ok) throw new Error("Could not update the entry.");
    } catch (e) {
      setError(e.message);
      fetchTasks();
    }
  }

  async function cyclePriority(task) {
    const order = ["low", "medium", "high"];
    const next = order[(order.indexOf(task.priority) + 1) % order.length];
    setTasks((prev) =>
      prev.map((t) => (t.id === task.id ? { ...t, priority: next } : t))
    );
    try {
      const res = await fetch(`${API}/${task.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ priority: next }),
      });
      if (!res.ok) throw new Error("Could not update priority.");
    } catch (e) {
      setError(e.message);
      fetchTasks();
    }
  }

  async function removeTask(id) {
    const prev = tasks;
    setTasks((cur) => cur.filter((t) => t.id !== id));
    try {
      const res = await fetch(`${API}/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Could not remove the entry.");
    } catch (e) {
      setError(e.message);
      setTasks(prev);
    }
  }

  const visible = useMemo(() => {
    let list = tasks;

    if (filter === "open") list = list.filter((t) => !t.done);
    else if (filter === "done") list = list.filter((t) => t.done);

    if (categoryFilter) list = list.filter((t) => t.category === categoryFilter);

    const q = search.trim().toLowerCase();
    if (q) list = list.filter((t) => t.title.toLowerCase().includes(q));

    const sorted = [...list];
    if (sort === "priority") {
      const rank = { high: 0, medium: 1, low: 2 };
      sorted.sort((a, b) => rank[a.priority] - rank[b.priority]);
    } else if (sort === "due_date") {
      sorted.sort((a, b) => {
        if (!a.due_date) return 1;
        if (!b.due_date) return -1;
        return a.due_date.localeCompare(b.due_date);
      });
    } else if (sort === "title") {
      sorted.sort((a, b) => a.title.localeCompare(b.title));
    } else {
      sorted.sort((a, b) => b.id - a.id);
    }
    return sorted;
  }, [tasks, filter, categoryFilter, search, sort]);

  const openCount = tasks.filter((t) => !t.done).length;

  return (
    <main className="sheet">
      <header className="sheet-head">
        <div className="head-row">
          <div>
            <p className="eyebrow">TaskLine — daily entries</p>
            <h1>Today's List</h1>
          </div>
          <button
            className="theme-toggle"
            onClick={() => setDark((d) => !d)}
            aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
            title={dark ? "Switch to light mode" : "Switch to dark mode"}
          >
            {dark ? "☀" : "☾"}
          </button>
        </div>
        <p className="tally">
          {openCount} open · {tasks.length} total
        </p>
      </header>

      <form className="entry-form" onSubmit={addTask}>
        <input
          className="title-input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Log a new task…"
          aria-label="New task"
        />
        <select
          className="priority-select"
          value={draftPriority}
          onChange={(e) => setDraftPriority(e.target.value)}
          aria-label="Priority"
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
        <button type="submit" disabled={!draft.trim()}>
          Add
        </button>
      </form>

      <div className="entry-form-secondary">
        <input
          className="category-input"
          value={draftCategory}
          onChange={(e) => setDraftCategory(e.target.value)}
          placeholder="Category (optional)"
          list="category-options"
          aria-label="Category"
        />
        <datalist id="category-options">
          {categories.map((c) => (
            <option key={c} value={c} />
          ))}
        </datalist>
        <input
          className="date-input"
          type="date"
          value={draftDue}
          onChange={(e) => setDraftDue(e.target.value)}
          aria-label="Due date"
        />
      </div>

      <div className="toolbar">
        <input
          className="search-input"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search entries…"
          aria-label="Search tasks"
        />
        <select
          className="category-filter"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          aria-label="Filter by category"
        >
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select
          className="sort-select"
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          aria-label="Sort by"
        >
          <option value="created">Newest</option>
          <option value="priority">Priority</option>
          <option value="due_date">Due date</option>
          <option value="title">Title</option>
        </select>
      </div>

      <nav className="filters" aria-label="Filter tasks">
        {["open", "all", "done"].map((f) => (
          <button
            key={f}
            className={filter === f ? "filter active" : "filter"}
            onClick={() => setFilter(f)}
          >
            {f}
          </button>
        ))}
      </nav>

      {error && <p className="error">{error}</p>}

      <ul className="ledger">
        {loading && <li className="empty">Reading the ledger…</li>}

        {!loading && visible.length === 0 && (
          <li className="empty">
            {filter === "done"
              ? "Nothing crossed off yet."
              : "Nothing logged. Add the first line above."}
          </li>
        )}

        {!loading &&
          visible.map((task) => (
            <li key={task.id} className={task.done ? "row done" : "row"}>
              <button
                className="check-btn"
                onClick={() => toggleTask(task)}
                aria-pressed={task.done}
                aria-label={task.done ? "Mark as open" : "Mark as done"}
              >
                <Check done={task.done} />
              </button>

              <div className="row-main">
                <span className="title">{task.title}</span>
                <div className="meta">
                  {task.category && (
                    <span className="chip category-chip">{task.category}</span>
                  )}
                  {task.due_date && (
                    <span className={task.overdue ? "chip due-chip overdue" : "chip due-chip"}>
                      {task.overdue ? "Overdue " : "Due "}
                      {formatDue(task.due_date)}
                    </span>
                  )}
                </div>
              </div>

              <button
                className={`priority-tag priority-${task.priority}`}
                onClick={() => cyclePriority(task)}
                title="Click to change priority"
              >
                {PRIORITY_LABEL[task.priority]}
              </button>
              <button
                className="remove-btn"
                onClick={() => removeTask(task.id)}
                aria-label={`Remove "${task.title}"`}
              >
                ✕
              </button>
            </li>
          ))}
      </ul>
    </main>
  );
}