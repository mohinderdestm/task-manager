# Notification Service

The Notification Service is microservice #5 in the Task Manager system. It handles all email notifications triggered by task events and direct user messages, using **Celery + Redis Cloud** for reliable background delivery via SendGrid.

---

## Features

- Webhook endpoint for task-service to trigger notifications on task creation
- Manual notification trigger per task with flexible recipient resolution
- Bulk notifications across multiple tasks and users
- Direct custom message endpoint for any user
- **Background task processing via Celery + Redis Cloud** with automatic retry (up to 3 attempts)
- Full notification history stored in MongoDB
- JWT authentication on all manual endpoints (PyJWT — matches auth-service)
- Graceful user name resolution handling both flat and nested profile structures from user-service

---

## Project Structure

```
notification-service/
│
├── notif/
│   ├── __init__.py
│   ├── dependencies.py       # JWT auth dependency (get_current_user)
│   ├── queue.py              # Legacy async queue (kept for reference, replaced by Celery)
│   └── router.py             # All API route definitions
│
├── celery_app.py             # Celery app + Redis Cloud broker configuration
├── tasks.py                  # Celery background task definitions (send_email_task)
├── database.py               # MongoDB Motor collections (notifications, users, tasks)
├── main.py                   # FastAPI app entry point
├── models.py                 # Pydantic request/response models
├── utils.py                  # JWT verify, email templates, SendGrid sender (async)
├── requirements.txt
└── .env
```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/notify/task-created` | ❌ No | Webhook called by task-service on task creation |
| POST | `/notify/task-updated/{task_id}` | ❌ No | Webhook called by task-service on task update |
| POST | `/notify/task/{task_id}` | ✅ Yes | Manually trigger a notification for a task |
| POST | `/notify/bulk` | ✅ Yes | Bulk notify multiple users for multiple tasks |
| POST | `/notify/user/{user_id}` | ✅ Yes | Send a custom direct message to a user |
| POST | `/notify/overdue` | ✅ Yes | Scan and notify all overdue tasks |
| POST | `/notify/retry/{notification_id}` | ✅ Yes | Retry a failed notification |
| PATCH | `/notify/{notification_id}/read` | ✅ Yes | Mark a notification as read |
| GET | `/notify/status` | ✅ Yes | List all notifications (filterable by status/type) |
| GET | `/notify/status/{notification_id}` | ✅ Yes | Get status of a specific notification |
| GET | `/notify/task/{task_id}/history` | ✅ Yes | Get notification history for a task |
| GET | `/notify/stats` | ✅ Yes | Aggregated counts by status and type |
| GET | `/notify/user/{user_id}/feed` | ✅ Yes | All notifications for a specific user |
| DELETE | `/notify/clear` | ✅ Admin | Wipe all notification records |
| DELETE | `/notify/{notification_id}` | ✅ Yes | Delete a specific notification record |
| GET | `/health` | ❌ No | Health check |

---

## Request Flow

```
task-service (POST /notify/task-created)
        ↓
Router receives webhook payload { task_id, assigned_to, title }
        ↓
Fetch user email + name from users collection
        ↓
Build email content via template (utils.py)
        ↓
Save notification doc to MongoDB (status: PENDING)
        ↓
.delay() pushes notification_id to Redis Cloud broker
        ↓
Celery worker picks up the task (running in separate process)
        ↓
Fetches doc from MongoDB, sends email via SendGrid
        ↓
Updates status: SENT or FAILED (retries up to 3x on failure)
```

---

## Notification Statuses

| Status | Meaning |
|--------|---------|
| `pending` | Created, waiting to be processed |
| `queued` | Picked up by Celery worker |
| `sent` | Successfully delivered via SendGrid |
| `failed` | Failed after max retries (3 attempts, 60s apart) |

---

## Notification Types

- `task_assigned` — new task assigned to user
- `task_completed` — task marked as completed
- `task_updated` — task details updated
- `task_deleted` — task deleted
- `task_overdue` — task past its due date

---

## Environment Variables

```env
MONGO_URI=           # MongoDB Atlas connection string
DB_NAME=             # Database name (task-manager)
SENDGRID_API_KEY=    # SendGrid API key
FROM_EMAIL=          # Sender email address
JWT_SECRET_KEY=      # Shared JWT secret (must match auth-service)
JWT_ALGORITHM=       # HS256
PORT=3004
REDIS_URL=           # Redis Cloud connection string (redis://default:password@host:port)
```

---

## Setup & Run

This service requires **two terminals** to run — one for FastAPI, one for the Celery worker.

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows PowerShell

# Install dependencies
pip install -r requirements.txt
```

**Terminal 1 — FastAPI server:**
```bash
uvicorn main:app --reload --port 3004
```

**Terminal 2 — Celery worker:**
```bash
celery -A celery_app worker --loglevel=info --pool=solo
```

> `--pool=solo` is required on Windows. On Linux/macOS use `--pool=prefork` instead.

---

## Architecture Notes

### Why Celery + Redis?
Previously the service used an in-memory asyncio queue (`queue.py`). This had one critical limitation — if the server restarted, all queued notifications were lost. Celery + Redis solves this:
- Tasks are persisted in Redis until a worker picks them up
- If the worker crashes mid-task, the task is re-queued automatically (`task_acks_late=True`)
- Workers can be scaled horizontally by running multiple instances

### Why pymongo in tasks.py instead of Motor?
Motor (the async MongoDB driver used in FastAPI) is tied to the asyncio event loop. Celery workers are synchronous — calling `asyncio.run()` inside a Celery task creates a new event loop each time, which conflicts with the Motor client created at startup. pymongo (sync) is used inside `tasks.py` to avoid this conflict. Both `motor` and `pymongo` are in `requirements.txt`.

---

## Integration Notes

- **auth-service** — JWT tokens are verified using PyJWT with the shared `JWT_SECRET_KEY`. The token payload includes `user_id`, `email`, and `role`.
- **task-service** — calls `POST /notify/task-created` and `POST /notify/task-updated/{task_id}` automatically. No auth token required on these endpoints.
- **user-service** — user names are resolved from MongoDB directly, supporting both top-level `name` field (set on signup) and nested `profile.name` (set after profile update via user-service).
- **analytics-service** — no direct interaction with notification-service.