# Repository Guidelines

## Project Structure & Module Organization

This repository is a small FastAPI service for cleaning base64-encoded HTML email content through Redis queues. `app.py` is only a compatibility entrypoint for `uvicorn app:app`; application code lives in `mailcleaner/`. Routes are in `mailcleaner/api.py`, app lifecycle is in `mailcleaner/main.py`, schemas are in `mailcleaner/schemas.py`, Redis setup is in `mailcleaner/redis_client.py`, worker code is in `mailcleaner/worker.py`, and business helpers are in `mailcleaner/services/`. Runtime packaging is defined by `Dockerfile` and `docker-compose.yml`; dependencies are pinned in `requirements.txt`.

## Build, Test, and Development Commands

- `python -m venv .venv && source .venv/bin/activate`: create and activate a local virtual environment.
- `pip install -r requirements.txt`: install FastAPI, Redis, BeautifulSoup, dotenv, and Uvicorn dependencies.
- `uvicorn app:app --reload --host 0.0.0.0 --port 8000`: run the API locally. Use a reachable Redis instance and matching `REDIS_*` variables.
- `docker compose up --build`: build and run the API plus Redis stack defined in Compose.
- `curl http://localhost:8000/health`: verify the service can connect to Redis.

## Coding Style & Naming Conventions

Use Python 3.13-compatible code and keep modules grouped by responsibility. Follow PEP 8 with 4-space indentation, `snake_case` for functions and variables, and `PascalCase` for Pydantic models such as `CleanerJob`. Keep request/response field aliases aligned with the existing external JSON contract (`jobId`, `resultQueue`, `base64Content`). Prefer typed function signatures and small pure helpers for parsing, encoding, and cleaning logic.

## Testing Guidelines

No test framework is configured yet. When adding tests, prefer `pytest` and place files under `tests/` using `test_*.py` names. Prioritize unit tests for `decode_base64`, `extract_readable_text`, `process_raw_job`, and Redis error handling. For API tests, use FastAPI's test client and mock Redis rather than requiring a live Redis server. Run future tests with `pytest`.

## Commit & Pull Request Guidelines

Recent history uses short messages such as `feat: convertido app para FastApi` and `update`. Prefer clearer conventional-style subjects going forward, for example `feat: add job validation` or `fix: handle empty redis password`. Pull requests should include a concise description, affected endpoints or queues, test evidence, and any environment-variable or Docker changes. Include example `curl` output when API behavior changes.

## Security & Configuration Tips

Do not commit `.env`, secrets, Redis passwords, virtual environments, or IDE folders. Keep defaults suitable for Docker Compose, but document any new required environment variable in `README.md` and this guide when it affects contributors.
