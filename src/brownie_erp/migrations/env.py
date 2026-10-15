from alembic import context
from sqlalchemy import create_engine

from brownie_erp.models import Base

config = context.config
target_metadata = Base.metadata


def run_migrations_online() -> None:
    engine = create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=True, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
