# Zeno - Daily Planning AI Assistant

## Project Overview

Zeno (formerly Jarvis) is an AI-powered daily planning assistant that provides:

- Morning briefings and schedule reviews
- Smart calendar management
- Weather and traffic updates
- Priority task reminders
- iOS app integration for seamless task management

## Directory Structure

```
zeno/
├── README.md
├── requirements.txt
├── docker-compose.yml
├── .env.example
├── PROJECT_STRUCTURE.md
│
├── agents/                     # AI Agent Layer
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── zeno_agent.py       # Main Zeno agent (renamed from Jarvis)
│   │   ├── daily_planning_agent.py  # Daily planning specialist
│   │   ├── workspace_agent.py  # Google Workspace integration
│   │   └── agent_session.py    # Enhanced session management
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── calendar_tools.py   # Calendar management
│   │   ├── task_tools.py       # Task management
│   │   ├── weather_tools.py    # Weather/traffic APIs
│   │   └── notification_tools.py  # Push notifications
│   └── workflows/
│       ├── __init__.py
│       ├── morning_briefing.py # Morning briefing workflow
│       ├── task_planning.py    # Task planning workflow
│       └── call_scheduling.py  # Outbound call scheduling
│
├── api/                        # REST API Layer
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py             # Authentication endpoints
│   │   ├── tasks.py            # Task management endpoints
│   │   ├── calendar.py         # Calendar endpoints
│   │   ├── briefings.py        # Morning briefing endpoints
│   │   ├── agent.py            # Agent interaction endpoints
│   │   └── ios.py              # iOS-specific endpoints
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py             # JWT authentication
│   │   └── cors.py             # CORS configuration
│   └── schemas/
│       ├── __init__.py
│       ├── user.py             # User data models
│       ├── task.py             # Task data models
│       ├── calendar.py         # Calendar data models
│       └── briefing.py         # Briefing data models
│
├── core/                       # Core Business Logic
│   ├── __init__.py
│   ├── daily_planning/
│   │   ├── __init__.py
│   │   ├── briefing_generator.py   # Morning briefing logic
│   │   ├── calendar_manager.py     # Calendar integration
│   │   ├── task_scheduler.py       # Task scheduling
│   │   └── priority_engine.py      # Task prioritization
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── google/
│   │   │   ├── __init__.py
│   │   │   ├── oauth.py            # Google OAuth
│   │   │   ├── calendar.py         # Google Calendar
│   │   │   ├── gmail.py            # Gmail integration
│   │   │   └── drive.py            # Google Drive
│   │   ├── weather/
│   │   │   ├── __init__.py
│   │   │   └── weather_api.py      # Weather service
│   │   └── traffic/
│   │       ├── __init__.py
│   │       └── traffic_api.py      # Traffic service
│   ├── notifications/
│   │   ├── __init__.py
│   │   ├── push_service.py         # Push notifications
│   │   └── call_service.py         # Outbound call service
│   └── storage/
│       ├── __init__.py
│       ├── database.py             # Database connections
│       ├── models.py               # SQLAlchemy models
│       └── repositories.py        # Data access layer
│
├── config/                     # Configuration Management
│   ├── __init__.py
│   ├── settings.py             # Unified settings
│   ├── database.py             # Database configuration
│   ├── livekit.py              # LiveKit configuration
│   └── environments/
│       ├── development.py
│       ├── staging.py
│       └── production.py
│
├── ios_backend/                # iOS App Backend Services
│   ├── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py     # User management
│   │   ├── sync_service.py     # Data synchronization
│   │   ├── push_service.py     # Push notifications
│   │   └── call_service.py     # Call scheduling
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── task.py
│   │   ├── schedule.py
│   │   └── preferences.py
│   └── utils/
│       ├── __init__.py
│       ├── jwt_utils.py
│       └── validation.py
│
├── scripts/                    # Utility Scripts
│   ├── setup.py               # Project setup
│   ├── migrate.py              # Database migrations
│   ├── init_oauth.py           # OAuth initialization
│   └── deploy.py               # Deployment scripts
│
├── tests/                      # Test Suite
│   ├── __init__.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── docs/                       # Documentation
│   ├── API.md                  # API documentation
│   ├── SETUP.md                # Setup instructions
│   ├── DAILY_PLANNING.md       # Daily planning features
│   └── IOS_INTEGRATION.md      # iOS integration guide
│
├── deployment/                 # Deployment Configuration
│   ├── docker/
│   │   ├── Dockerfile.api
│   │   ├── Dockerfile.agent
│   │   └── docker-compose.yml
│   ├── kubernetes/
│   └── terraform/
│
└── legacy/                     # Legacy Jarvis Code (for reference)
    └── voice-starter/          # Current voice-starter directory
```

## Key Features

### Daily Planning Core

- **Morning Briefings**: Automated daily schedule reviews
- **Calendar Management**: Smart calendar integration and conflict resolution
- **Weather & Traffic**: Real-time updates for commute planning
- **Task Prioritization**: AI-driven task ranking and scheduling

### iOS App Integration

- **REST API**: Comprehensive API for iOS app communication
- **Push Notifications**: Real-time updates and reminders
- **Data Sync**: Seamless synchronization between app and backend
- **Call Scheduling**: Automated outbound calls for updates

### Agent System

- **Modular Agents**: Specialized agents for different functions
- **Workflow Management**: Orchestrated workflows for complex tasks
- **Tool Integration**: Rich set of tools for calendar, tasks, and notifications

## Technology Stack

### Backend

- **LiveKit Agents**: Voice AI and conversation management
- **FastAPI**: REST API framework
- **SQLAlchemy**: Database ORM
- **PostgreSQL**: Primary database
- **Redis**: Caching and session storage

### Integrations

- **Google Workspace**: Calendar, Gmail, Drive
- **Weather APIs**: Real-time weather data
- **Traffic APIs**: Traffic and navigation data
- **Push Notifications**: APNs for iOS

### Infrastructure

- **Docker**: Containerization
- **Kubernetes**: Orchestration
- **Terraform**: Infrastructure as Code
