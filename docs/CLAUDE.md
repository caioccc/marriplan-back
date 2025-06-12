# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tutoriando is a Django-based educational tutoring application that integrates with Ollama LLM to provide AI-powered tutoring assistance. The backend serves a REST API for chat-based tutoring sessions with a focus on ENEM (Brazilian standardized test) preparation.

## Key Technologies

- Django 4.2 + Django REST Framework 3.15.2
- PostgreSQL (primary) / SQLite (fallback)
- Ollama for LLM integration
- Knox for token authentication
- Docker for containerization

## Essential Commands

### Development

```bash
# Start development server
python manage.py runserver

# Run tests
python manage.py test

# Check code style
flake8

# Database operations
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### Docker Development

```bash
# Start full stack with PostgreSQL
docker-compose up --build

# Alternative Docker method
docker build -t backend .
docker run -p 8000:8000 backend
```

### Production Build

```bash
# Run the build script for deployment
./build.sh
```

## Architecture Overview

### Core Structure

- **app/** - Main Django application
  - **core/** - Core functionality including LLM integration
    - **models/llm/** - Ollama LLM integration (chat.py, thinking.py, system.py)
    - **models/embedding/** - Embedding models
  - **data/raw/ENEM/** - ENEM exam questions and images
  - **views.py** - Main API views (ChatView, SessionView, etc.)
  - **viewsets.py** - DRF viewsets for CRUD operations

### Key Models (models.py)

- **CustomUser** - Extended user model with 2FA support
- **UserSettings** - User preferences (theme, language)
- **Session** - Chat session management
- **ChatMessage** - Message history with thinking support

### Authentication Flow

- Token-based authentication using Knox
- 2FA support with TOTP
- Login endpoint returns token to be used as: `Token <token_hash>`

### API Documentation

Swagger/OpenAPI documentation available at `/swagger/`

### Custom Management Commands

- `python manage.py starter <password>` - Creates superuser with specified password
- `python manage.py wait_for_db` - Waits for database connection (useful in Docker)

## Development Notes

### Default Credentials
- Username: admin
- Password: Admin123!

### Code Style
- Flake8 configured with max-line-length=120
- Excludes migrations from linting

### Environment Variables
Development environment variables are in `.env.dev` (referenced in docker-compose.yaml)

### LLM Integration
The application uses Ollama for LLM functionality. The integration is handled in `app/core/models/llm/` with:
- System prompts configured to respond in Portuguese
- Thinking/reasoning support for complex responses
- Chat history management for context awareness