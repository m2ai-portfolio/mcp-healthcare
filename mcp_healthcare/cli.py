"""Click CLI entrypoint for MCP Healthcare."""

import click
import logging
import sys

from . import __version__
from .config import get_settings
from .db import init_database


def setup_logging(level: str = "INFO") -> None:
    """Configure logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )


@click.group()
@click.version_option(version=__version__)
@click.option(
    "--log-level",
    default=None,
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    help="Set logging level (overrides MCP_LOG_LEVEL env var)"
)
@click.pass_context
def main(ctx, log_level):
    """MCP Healthcare Clinical Decision Support Server.

    A local-only clinical decision support system providing:
    - Medication interaction checking
    - Clinical pathway recommendations
    - HIPAA-compliant audit logging
    """
    # Ensure ctx.obj exists
    ctx.ensure_object(dict)

    # Get settings
    settings = get_settings()

    # Set up logging
    level = log_level or settings.mcp_log_level
    setup_logging(level)
    ctx.obj["logger"] = logging.getLogger(__name__)

    # Store settings in context
    ctx.obj["settings"] = settings


@main.command()
@click.pass_context
def init(ctx):
    """Initialize the database and data directory."""
    settings = ctx.obj["settings"]
    logger = ctx.obj["logger"]

    try:
        # Ensure data directory exists
        settings.ensure_data_dir()
        click.echo(f"Created data directory: {settings.data_dir_path}")

        # Initialize database
        db_manager = init_database()
        click.echo(f"Initialized database: {settings.db_path}")

        # Verify schema
        if db_manager.verify_schema():
            click.echo("Database schema verified successfully")
            logger.info("Database initialization complete")
        else:
            click.echo("Warning: Database schema verification failed", err=True)
            logger.warning("Database schema verification failed")

        db_manager.close()

    except Exception as e:
        click.echo(f"Error during initialization: {e}", err=True)
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)


@main.command()
@click.pass_context
def status(ctx):
    """Show current configuration and system status."""
    settings = ctx.obj["settings"]

    click.echo("\nMCP Healthcare Configuration:")
    click.echo(f"  Data Directory: {settings.data_dir_path}")
    click.echo(f"  Database: {settings.db_path}")
    click.echo(f"  Log Level: {settings.mcp_log_level}")
    click.echo(f"  Audit Logging: {'Enabled' if settings.mcp_audit_enable else 'Disabled'}")

    # Check if database exists
    if settings.db_path.exists():
        click.echo(f"\n  Database Status: Exists ({settings.db_path.stat().st_size} bytes)")

        # Try to verify schema
        try:
            from .db import DatabaseManager
            db_manager = DatabaseManager()
            if db_manager.verify_schema():
                click.echo("  Schema Status: Valid")
            else:
                click.echo("  Schema Status: Invalid or not initialized")
            db_manager.close()
        except Exception as e:
            click.echo(f"  Schema Status: Error - {e}")
    else:
        click.echo("\n  Database Status: Not initialized (run 'mcp-healthcare init')")


if __name__ == "__main__":
    main()
