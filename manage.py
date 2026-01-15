import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
from alembic import command
from alembic.config import Config

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

current_dt = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M")

DATABASE_URL = os.getenv("DATABASE_URL")
ALEMBIC_CONFIG = "alembic.ini"


def get_alembic_config() -> Config:
    if DATABASE_URL is None:
        raise Exception("DATABASE_URL is not set")

    config = Config(ALEMBIC_CONFIG)
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    return config


@click.group()
def cli() -> None:
    pass


@click.command()
@click.option("-m", "--message", type=str)
@click.option("-a", "--autogenerate", type=bool, default=True)
def makemigrations(autogenerate: bool, message: str) -> None:
    """Generates migration scripts."""
    logger.info("Generating new migration...")
    alembic_cfg = get_alembic_config()
    command.revision(alembic_cfg, autogenerate=autogenerate, message=message)


@click.command()
@click.option("-r", "--revision", type=str)
def migrate(revision: str) -> None:
    """
    Applies migration by the given revision id.
    """
    logger.info(f"Applying migrations... revision number: {revision}.")
    click.confirm(
        "Have you reviewed the SQL code in the upgrade() method of the migration? "
        "Does it align with your expectations?",
        abort=True,
    )
    alembic_cfg = get_alembic_config()
    command.upgrade(alembic_cfg, revision=revision)


@click.command()
@click.option("-r", "--revision", type=str)
def sql(revision: str) -> None:
    """
    Command to get the sql scripts for the generated migration, requires revision id.
    Revision id can be used in format "<old_revision>:<new_revision>" to get sql only for specified range of revisions.

    <old_revision> can be received via current-migration command.
    """
    alembic_cfg = get_alembic_config()
    command.upgrade(alembic_cfg, revision=revision, sql=True)


@click.command()
@click.option("-v", "--verbose", type=bool, default=False)
def current_migration(verbose: bool) -> None:
    """
    Can be used to get a revision ID of the latest applied migration.
    Be aware, this command doesn't return not applied local migrations.
    """
    alembic_cfg = get_alembic_config()
    command.current(alembic_cfg, verbose=verbose)


@click.command()
@click.option("-r", "--revision", type=str)
def rollback(revision: str) -> None:
    """
    If you want to rollback database state use this command.
    Specify "base" as revision parameter to rollback database to it's initial state.
    """

    logger.info(f"Applying rollback... revision number: {revision}")
    click.confirm(
        "Have you reviewed the SQL code in the downgrade() method of the migration? "
        "Does it align with your expectations?",
        abort=True,
    )
    alembic_cfg = get_alembic_config()
    command.downgrade(alembic_cfg, revision=revision)


@click.command()
def rename_default_python_filenames() -> None:
    """
    Command is used to rename python filenames into latest supported format.
    Legacy format: <revision_id>_<slug>.py
    New format: <YYYY-MM-DD>_<revision_id>-<slug>.py
    """

    unsupported_filename_pattern = re.compile(r"\w{12}_\w*.py")

    migration_metadata_search_pattern = re.compile(
        r'"""(?P<slug>.+?)\n\n'
        r"Revision ID: (?P<revision_id>\w{12})\n"
        r"Revises: *[^\n]*\n"
        r"Create Date: (?P<date>\d{4}-\d{2}-\d{2})",
        re.DOTALL,  # Allows '.' to match newline characters
    )

    directory = Path("alembic/versions")
    unsupported_python_files = [
        file for file in directory.iterdir() if file.is_file() and unsupported_filename_pattern.match(file.name)
    ]

    logger.info("Please review that the file that will be updated are expected:")
    for file in unsupported_python_files:
        logger.info(file.name)
    click.confirm("Does it align with your expectations?", abort=True)

    # renaming python files
    for file in unsupported_python_files:
        migration_content = file.read_text()
        metadata_search_obj = migration_metadata_search_pattern.search(migration_content)

        created_date = None
        revision_number = None
        slug = None

        if metadata_search_obj:
            created_date = metadata_search_obj.group("date")
            revision_number = metadata_search_obj.group("revision_id")
            slug = metadata_search_obj.group("slug")
        else:
            logger.error(f"Unable to parse migration content to get required fields for {file.name}")
            continue

        new_path = file.with_name(f"{created_date}_{revision_number}-{slug}.py")
        click.confirm(f"Going to rename: {file.name} -> {new_path.name}", abort=True)
        file.rename(new_path)


@click.command()
def rename_default_sql_filenames() -> None:
    """
    Command is used to rename legacy sql filenames into latest supported format.
    Have to be executed after rename-default-python-files

    Legacy format: <revision_id>_<slug>.sql
    New format: <YYYY-MM-DD>_<revision_id>-<slug>.sql
    """
    click.confirm(
        text=(
            "This command has to be executed after all python files are renamed with rename-default-python-files "
            "command. "
            "Have you executed it before? Make sure all python files are properly updated. Continue?"
        ),
        abort=True,
    )

    unsupported_filename_pattern = re.compile(r"\w{12}_\w*.sql")

    sql_files_directory = Path("alembic/sql_scripts")
    python_migration_directory = Path("alembic/versions")

    unsupported_sql_files = [
        file
        for file in sql_files_directory.iterdir()
        if file.is_file() and unsupported_filename_pattern.match(file.name)
    ]
    python_migration_file_names = [file.name for file in python_migration_directory.iterdir()]

    # renaming sql files
    for file in unsupported_sql_files:
        revision_number = file.name.split("_")[0]

        new_sql_filename = None
        for python_file_name in python_migration_file_names:
            if revision_number in python_file_name:
                # dropping .py extension
                new_sql_filename = python_file_name[:-3]
                continue

        if new_sql_filename is None:
            logger.error(f"Unable to get updated sql name for {file.name}")
            continue

        new_path = file.with_name(f"{new_sql_filename}.sql")
        click.confirm(f"Going to rename: {file.name} -> {new_path.name}", abort=True)
        file.rename(new_path)


# call: python manage.py --help to see available commands
# call python manage.py <command> --help to see available options for a specific command
if __name__ == "__main__":
    cli.add_command(makemigrations)
    cli.add_command(migrate)
    cli.add_command(current_migration)
    cli.add_command(sql)
    cli.add_command(rollback)
    cli.add_command(rename_default_python_filenames)
    cli.add_command(rename_default_sql_filenames)

    cli()
    # makemigrations(True, "initial_setup")
