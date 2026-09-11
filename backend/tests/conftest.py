"""Shared pytest configuration.

Import-time env setup so that every test module (regardless of import order)
gets a throwaway SQLite database and deterministic mock literature mode.
This avoids accidentally connecting to the real PostgreSQL from `.env`.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./_test_e2e.db")
os.environ.setdefault("LITERATURE_MODE", "mock")