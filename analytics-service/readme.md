# Analytics Service

The Analytics Service is responsible for generating insights and statistics from user tasks such as completion rate, productivity, and task distribution.

## Features

- Generate task completion statistics
- Analyze tasks by status (completed, pending, overdue)
- Provide user productivity metrics
- Provide analytics for dashboards


## Project Structure

analytics-service/
│
├── app/
│   ├── database/      # MongoDB connection
│   ├── routes/        # API endpoints
│   ├── services/      # Business logic for analytics
│   ├── utils/         # Helper functions
│   ├── config.py      # Configuration settings
│   └── main.py        # FastAPI entry point
│
├── .env               # Environment variables
└── run.py             # Service runner


## Run Service

python run.py