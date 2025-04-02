# BittensorDividends
An asynchronous API service for querying Bittensor blockchain data and performing sentiment-based staking operations.


## Project Structure

```
src/
├── api/                  # API endpoints
├── core/                 # Authentication and security & App Config  & App Lifecycle Events
├── db/                   # Database models
├── services/             # Third Party Services
├── schemas/              # API Pydantic Schemas
├── tests/                # API Unit Tests
├── celery_worker.py      # Celery background tasks

main.py                   # FastAPI application

docker-compose.yml        # Docker Compose configuration
Dockerfile                # Docker image specification
requirements.txt          # Python dependencies
```

## Features

- **Async Blockchain Queries**: FastAPI endpoints for querying TAO dividends with Redis caching
- **Sentiment Analysis**: Analyzes Twitter sentiment about Bittensor subnets using Datura.ai and Chutes.ai
- **Auto-Staking**: Automatically stakes or unstakes TAO based on sentiment scores
- **Highly Concurrent**: Designed to handle ~1000 concurrent requests efficiently
- **Containerized**: All components run in Docker containers for easy deployment

## Architecture

- **FastAPI**: Asynchronous API framework
- **Redis**: Caching and Celery message broker
- **Celery**: Background processing for sentiment analysis and staking
- **PostgreSQL**: Persistent storage for transaction history
- **AsyncSubtensor**: Asynchronous blockchain interactions
- **Docker**: Container orchestration



### Environment Variables

Create a `.env` file with your credentials defined in `.env.example`

    API_KEY=YourSecretApiKey
    API_KEY_HEADER=X-API-Key

### Running with Docker

docker compose build && docker compose up

### Running without using Docker

First, create a venv: `python -m venv my-env`

Then install the dependencies: `pip install -r requirements.txt`

Then,
```bash
python main.py
```
and,
```bash
celery -A src.celery_worker.celery_app worker --loglevel=info --pool=threads
```

## Running pytest
```bash
# Run tests
pytest -s src/tests/test_divisends_api.py
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc


## API Endpoints

### GET /api/v1/tao_dividends

Query Tao dividends from the Bittensor blockchain.

**Parameters:**
- `netuid` (optional): Subnet ID
- `hotkey` (optional): Account hotkey
- `trade` (optional, default: false): Whether to trigger sentiment analysis and auto-staking

**Authentication:**
- API Key `X-API-Key` header
