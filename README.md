# Zeno - Daily Planning AI Assistant

Zeno is an AI-powered daily planning assistant that helps you start your day prepared and organized. Get morning briefings, smart calendar management, weather updates, and priority task reminders - all through voice interaction and a companion iOS app.

## 🌟 Features

### Daily Planning

- **Morning Briefings**: Automated daily schedule reviews and preparation
- **Smart Calendar Management**: Intelligent calendar integration with conflict resolution
- **Weather & Traffic Updates**: Real-time information for your commute planning
- **Priority Task Reminders**: AI-driven task ranking and scheduling

### iOS Integration

- **Voice Calls**: Zeno calls you at scheduled times for updates and briefings
- **Task Sharing**: Share your daily to-dos through the mobile app
- **Real-time Sync**: Seamless synchronization between voice interactions and app
- **Push Notifications**: Timely reminders and updates

### AI Agent System

- **Voice Interaction**: Natural voice conversations powered by LiveKit
- **Multi-Agent Architecture**: Specialized agents for different functions
- **Tool Integration**: Rich integration with Google Workspace, weather, and traffic APIs
- **Workflow Orchestration**: Sophisticated workflows for complex daily planning tasks

## 🏗️ Architecture

### Core Components

```
├── agents/          # AI Agent Layer (LiveKit-based voice agents)
├── api/            # REST API Layer (FastAPI for iOS integration)
├── core/           # Business Logic (daily planning, integrations)
├── ios_backend/    # iOS-specific backend services
├── config/         # Configuration management
└── legacy/         # Previous Jarvis implementation
```

### Technology Stack

- **AI & Voice**: LiveKit Agents, OpenAI GPT, Deepgram STT/TTS
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, Redis
- **Integrations**: Google Workspace APIs, Weather APIs, APNs
- **Infrastructure**: Docker, Kubernetes (deployment ready)

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Redis 6+
- Google Workspace API credentials
- LiveKit server access

### Installation

1. **Clone and setup environment**:

   ```bash
   git clone <repository-url>
   cd zeno
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:

   ```bash
   cp .env.example .env
   # Edit .env with your configuration values
   ```

4. **Setup database**:

   ```bash
   # Database migrations will be created in future iterations
   ```

5. **Initialize Google OAuth**:
   ```bash
   python scripts/init_oauth.py
   ```

### Running the Application

**Development Mode**:

```bash
# Start the API server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Start the LiveKit agent (separate terminal)
python -m agents.core.zeno_agent
```

**Production Mode**:

```bash
# Using Docker Compose
docker-compose up -d
```

## 📱 iOS Integration

The iOS app connects to Zeno through the REST API for:

- **User Authentication**: JWT-based secure authentication
- **Task Management**: CRUD operations for daily tasks
- **Calendar Sync**: Real-time calendar synchronization
- **Briefing Requests**: On-demand morning briefings
- **Call Scheduling**: Schedule Zeno to call you at specific times

### API Endpoints

- `POST /auth/login` - User authentication
- `GET /briefings/morning` - Get morning briefing
- `POST /tasks` - Create new task
- `GET /calendar/today` - Get today's calendar
- `POST /calls/schedule` - Schedule a call from Zeno

## 🔧 Configuration

### Environment Variables

See `.env.example` for all available configuration options.

### Google Workspace Setup

1. Create a Google Cloud Project
2. Enable Calendar, Gmail, and Drive APIs
3. Create OAuth 2.0 credentials
4. Download client secrets and place in `./credentials/`

### LiveKit Setup

1. Sign up for LiveKit Cloud or deploy your own server
2. Get API credentials
3. Configure in `.env` file

## 🏃‍♂️ Development

### Project Structure

The project follows a modular architecture:

- **Agents**: Voice AI components using LiveKit
- **API**: REST endpoints for iOS and external integrations
- **Core**: Business logic and service layer
- **iOS Backend**: Specialized services for mobile app

### Adding New Features

1. **Voice Features**: Extend agents in `agents/` directory
2. **API Features**: Add routes in `api/routes/`
3. **Business Logic**: Implement in `core/` modules
4. **iOS Features**: Add services in `ios_backend/`

## 📚 Documentation

- [API Documentation](docs/API.md) - REST API reference
- [Setup Guide](docs/SETUP.md) - Detailed setup instructions
- [Daily Planning Features](docs/DAILY_PLANNING.md) - Feature documentation
- [iOS Integration](docs/IOS_INTEGRATION.md) - Mobile app integration guide

## 🚢 Deployment

### Docker

```bash
# Build and run with Docker Compose
docker-compose up -d
```

### Kubernetes

```bash
# Apply Kubernetes manifests
kubectl apply -f deployment/kubernetes/
```

### Manual Deployment

Refer to `deployment/` directory for infrastructure templates and deployment scripts.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

- Create an issue in the GitHub repository
- Check the documentation in the `docs/` directory
- Review the legacy implementation in `legacy/voice-starter/`
