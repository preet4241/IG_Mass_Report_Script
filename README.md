# Instagram Report API & Bot

A robust Flask-based API for Instagram reporting integrated with a Telegram Bot management panel.

## Features
- **Instagram Reporting API**: Endpoints to submit reports for various categories (spam, nudity, hate speech, etc.).
- **Telegram Bot Panel**: Manage API keys, track usage statistics, and set custom domains directly via Telegram.
- **Security**: UUID-based API key validation with expiration tracking.
- **Scalability**: Designed to run with Gunicorn for production environments.

## Project Structure
- `main.py`: Flask application and API entry point.
- `bot.py`: Telegram Bot logic and management interface.
- `requirements.txt`: Python dependency list.
- `api_keys.json`: Local storage for API keys (generated automatically).
- `domain.json`: Local storage for bot domain configuration.

## Setup Instructions

### 1. Environment Secrets
Set the following secrets in your Replit environment:
- `BOT_TOKEN`: Your Telegram Bot API token.
- `OWNER_ID`: Your Telegram User ID (numeric).

### 2. Installation
The project automatically installs dependencies via `requirements.txt`. To manually install:
```bash
pip install -r requirements.txt
```

### 3. Running the Application
The application is configured to run via Gunicorn:
```bash
gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 1 --timeout 120 main:app
```

## API Endpoints
- `GET /`: API health check and info.
- `GET /api/report`: Submit a report (requires `key`, `ses`, `rep`, `target`).
- `GET /api/create_key`: Generate a new API key (Admin only).
- `GET /api/check_key`: Verify key status and usage.

## Credits
Developed for @PR_Bot_Services
