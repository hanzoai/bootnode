"""Tests for database session DSN handling."""

from bootnode.db.session import _ensure_async_dsn


def test_postgresql_converted():
    """Standard postgresql:// is converted to asyncpg."""
    dsn = "postgresql://user:pass@host:5432/db"
    assert _ensure_async_dsn(dsn) == "postgresql+asyncpg://user:pass@host:5432/db"


def test_postgres_converted():
    """Short-form postgres:// is converted to asyncpg."""
    dsn = "postgres://user:pass@host:5432/db"
    assert _ensure_async_dsn(dsn) == "postgresql+asyncpg://user:pass@host:5432/db"


def test_asyncpg_unchanged():
    """Already correct DSN is returned as-is."""
    dsn = "postgresql+asyncpg://user:pass@host:5432/db"
    assert _ensure_async_dsn(dsn) == dsn


def test_production_dsn():
    """Matches the actual K8s DATABASE_URL format."""
    dsn = "postgresql://bootnode:secret@postgres.bootnode.svc:5432/bootnode"
    expected = "postgresql+asyncpg://bootnode:secret@postgres.bootnode.svc:5432/bootnode"
    assert _ensure_async_dsn(dsn) == expected


def test_only_first_occurrence_replaced():
    """Only the scheme prefix is replaced, not embedded substrings."""
    dsn = "postgresql://user:postgresql@host:5432/postgresql"
    result = _ensure_async_dsn(dsn)
    assert result == "postgresql+asyncpg://user:postgresql@host:5432/postgresql"
