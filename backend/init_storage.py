"""Explicit initial schema provisioning. Run before API/worker deployment."""
from app.core.config import get_settings
from app.repositories.sql import Database
from app.workers import durable  # register the queue table

if __name__ == '__main__':
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError('DATABASE_URL is required')
    database = Database(settings.database_url)
    try:
        database.initialize()
    finally:
        database.engine.dispose()
