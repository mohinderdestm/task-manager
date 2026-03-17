# Notification Service

The Notification Service is microservice #5 in the Task Manager system. It handles all email notifications triggered by task events and direct user messages, using an async queue for reliable delivery via SendGrid.

---

## Features

- Webhook endpoint for task-service to trigger notifications on task creation
- Manual notification trigger per task with flexible recipient resolution
- Bulk notifications across multiple tasks and users
- Direct custom message endpoint for any user
- Async queue worker with automatic retry (up to 3 attempts) and exponential backoff
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
│   ├── queue.py              # Async notification queue worker
│   └── router.py             # All API route definitions
│
├── database.py               # MongoDB collections (notifications, users, tasks)
├── main.py                   # FastAPI app entry point + queue worker lifespan
├── models.py                 # Pydantic request/response models
├── utils.py                  # JWT verify, email templates, SendGrid sender
├── requirements.txt
└── .env
```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/notify/task-created` | ❌ No | Webhook called by task-service on task creation |
| POST | `/notify/task/{task_id}` | ✅ Yes | Manually trigger a notification for a task |
| POST | `/notify/bulk` | ✅ Yes | Bulk notify multiple users for multiple tasks |
| POST | `/notify/user/{user_id}` | ✅ Yes | Send a custom direct message to a user |
| GET | `/notify/status` | ✅ Yes | List all notifications (filterable by status/type) |
| GET | `/notify/status/{notification_id}` | ✅ Yes | Get status of a specific notification |
| GET | `/notify/task/{task_id}/history` | ✅ Yes | Get notification history for a task |
| POST | `/notify/task-updated/{task_id}` | ❌ No | Webhook called by task-service on task update |
| POST | `/notify/overdue` | ✅ Yes | Scan and notify all overdue tasks |
| POST | `/notify/retry/{notification_id}` | ✅ Yes | Retry a failed notification |
| PATCH | `/notify/{notification_id}/read` | ✅ Yes | Mark a notification as read |
| GET | `/notify/stats` | ✅ Yes | Aggregated counts by status and type |
| GET | `/notify/user/{user_id}/feed` | ✅ Yes | All notifications for a specific user |
| DELETE | `/notify/clear` | ✅ Admin | Wipe all notification records |
| DELETE | `/{notification_id}` | ✅ Yes | Delete a specific notification record |
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
Push notification_id to async queue
        ↓
Queue worker picks it up → sends via SendGrid
        ↓
Update status: SENT or FAILED (with retry logic)
```

---

## Notification Statuses

| Status | Meaning |
|--------|---------|
| `pending` | Created, waiting to be processed |
| `queued` | Picked up by queue worker |
| `sent` | Successfully delivered via SendGrid |
| `failed` | Failed after max retries (3 attempts) |

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
```

---

## Setup & Run

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn main:app --reload --port 3004
```

---

## Integration Notes

- **auth-service** — JWT tokens are verified using PyJWT with the shared `JWT_SECRET_KEY`. The token payload includes `user_id`, `email`, and `role`.
- **task-service** — calls `POST /notify/task-created` automatically when a task is created. No auth token required on this endpoint.
- **user-service** — user names are resolved from MongoDB directly, supporting both top-level `name` field (set on signup) and nested `profile.name` (set after profile update via user-service).
- **analytics-service** — no direct interaction with notification-service.