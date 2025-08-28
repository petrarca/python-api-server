import logging
import os
import sys
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# Configure loguru
LOG_LEVEL = os.getenv("API_SERVER_LOG_LEVEL", "INFO").upper()
logger.remove()  # Remove default handler
logger.add(sys.stderr, level=LOG_LEVEL)  # Add stderr handler with configurable level

# Enable SQL echo if log level is DEBUG or lower
SQL_ECHO = bool(os.getenv("API_SERVER_LOG_LEVEL", "True"))
logger.info(f"SQL echo is {'enabled' if SQL_ECHO else 'disabled'}")


# Create an intercept handler for standard logging to route to loguru
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


load_dotenv()

from api_server.database import DATABASE_URL  # noqa: E402

# Import all models to ensure they're registered with SQLModel metadata
from api_server.models import db_model  # noqa: F401, E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url in alembic.ini with the URL from our application
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret the config file for Python logging,
# but redirect everything through loguru
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
    # Redirect all standard logging to loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in logging.root.manager.loggerDict:
        logging_logger = logging.getLogger(name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

# Set SQLModel metadata as the target for migrations
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    logger.info(f"Running offline migrations with URL: {url}")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Handle circular foreign key dependencies
        render_as_batch=True,
        # Enable SQL echo if log level is DEBUG or lower
        echo=SQL_ECHO,
    )

    with context.begin_transaction():
        logger.info("Starting offline migration")
        context.run_migrations()
        logger.success("Offline migration completed successfully")


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    logger.info("Setting up database connection for online migrations")

    # Get config and override echo setting
    engine_config = config.get_section(config.config_ini_section, {})
    # Enable SQL echo if log level is DEBUG or lower
    engine_config["sqlalchemy.echo"] = str(SQL_ECHO).lower()

    connectable = engine_from_config(
        engine_config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        logger.info("Database connection established")
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Handle circular foreign key dependencies
            render_as_batch=True,
            # Compare types for PostgreSQL
            compare_type=True,
            # Enable SQL echo if log level is DEBUG or lower
            echo=SQL_ECHO,
        )

        with context.begin_transaction():
            logger.info("Starting online migration")
            context.run_migrations()
            logger.success("Online migration completed successfully")


if context.is_offline_mode():
    logger.info("Running in offline mode")
    run_migrations_offline()
else:
    logger.info("Running in online mode")
    run_migrations_online()
