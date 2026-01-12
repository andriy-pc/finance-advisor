import logging
from logging.config import fileConfig
from typing import Any

# do not delete this import since it's an initialization of the models from metric normalization rules
from alembic import context
from sqlalchemy import create_engine

from advisor.db.db_models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info(f"SQL alchemy tables: {Base.metadata.tables.keys()}")


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_object(object: Any, name: str, type_: str, reflected: bool, compare_to: Any) -> bool:
    """Method to allow alembic work only with databases in this project"""

    # Allow only databases from Base
    if type_ == "table":
        return name in Base.metadata.tables
    # Detect changes
    if type_ in (
        "column",
        "index",
        "foreign_key_constraint",
        "unique_constraint",
        "check_constraint",
        "primary_key",
    ):
        return True
    else:
        return False


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise ValueError("sqlalchemy.url is not set in alembic.ini")
    context.configure(
        url=url,
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,  # type: ignore
        version_table="ALEMBIC_FINANCE_ADVISOR_MIGRATIONS",
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise ValueError("sqlalchemy.url is not set in alembic.ini")
    connectable = create_engine(url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            include_object=include_object,  # type: ignore
            compare_type=True,
            version_table="ALEMBIC_FINANCE_ADVISOR_MIGRATIONS",
        )
    with context.begin_transaction():
        context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
