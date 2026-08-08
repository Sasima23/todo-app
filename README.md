# TaskLine — React + Flask Todo App

A small full-stack task list. Flask serves a JSON REST API backed by SQLite;
React (Vite) is the frontend.

## Structure

```
todo-app/
├── backend/
│   ├── app.py            # Flask API (GET/POST/PATCH/DELETE /api/tasks)
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js    # proxies /api → http://localhost:5000
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── App.css
        └── index.css
```

## Run the backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
python app.py
```

This starts the API at `http://localhost:5000` and creates `tasks.db`
(SQLite) on first run.

## Run the frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

This starts the dev server at `http://localhost:5173`. Requests to `/api/*`
are proxied to the Flask server, so no CORS setup is needed in dev (CORS is
enabled on the backend too, for production splits).

## API

| Method | Path              | Body                        | Description          |
|--------|-------------------|------------------------------|-----------------------|
| GET    | /api/tasks        | —                             | List all tasks        |
| POST   | /api/tasks        | `{ "title": "..." }`          | Create a task          |
| PATCH  | /api/tasks/:id    | `{ "title"?, "done"? }`       | Update a task          |
| DELETE | /api/tasks/:id    | —                             | Delete a task          |

## Production build

```bash
cd frontend
npm run build       # outputs static files to frontend/dist
```

Serve `frontend/dist` with any static host (or have Flask serve it) and point
it at a deployed Flask backend.
