"""Alembic environment configuration."""
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config as app_config
from models import Base

target_metadata = Base.metadata


def get_url():
    return getattr(app_config, "DATABASE_URL", None) or f"sqlite:///{app_config.DB_PATH}"


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    from alembic import config as alembic_cfg

    cfg = context.config
    cfg.set_main_option("sqlalchemy.url", get_url())
    connectable = engine_from_config(
        cfg.get_section(cfg.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
