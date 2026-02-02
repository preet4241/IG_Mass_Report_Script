# Instagram Report API

## Overview
A Flask-based API service with an optional Telegram bot for managing Instagram reporting functionality. The API allows creating and managing API keys, and the Telegram bot provides a management interface.

## Project Structure
- `main.py` - Flask API server with reporting endpoints
- `bot.py` - Telegram bot for API key management
- `requirements.txt` - Python dependencies

## Environment Variables
The following environment variables are required for the Telegram bot functionality:
- `BOT_TOKEN` - Telegram Bot API token (optional - bot disabled if not set)
- `OWNER_ID` - Telegram user ID of the bot owner (optional - bot disabled if not set)

Note: The Flask API works without these variables; only the Telegram bot requires them.

## API Endpoints
- `GET /` - API status and information
- `GET /api/report` - Submit a report (requires API key)
- `GET /api/create_key` - Create a new API key (requires admin password)
- `GET /api/check_key` - Check API key status

## Running Locally
The application runs on port 5000:
```bash
python main.py
```

## Data Storage
- `api_keys.json` - Stores API key data
- `domain.json` - Stores domain configuration for the Telegram bot
