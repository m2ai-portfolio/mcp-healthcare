"""Click CLI entrypoint for MCP Healthcare."""

import click
import json
import logging
import sys

from . import __version__
from .config import get_settings
from .db import init_database
from .models import MedicationInput, ObservationBundle
from .drug_checker import DrugInteractionChecker
from .diagnostic import DiagnosticEvaluator


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


@main.command("drug-check")
@click.option("--medications", "-m", required=True, help="JSON array of medication objects")
@click.option("--user-id", "-u", default="cli-user", help="User ID for audit logging")
@click.pass_context
def drug_check(ctx, medications, user_id):
    """Check drug interactions for a medication list.

    Example:
        mcp-healthcare drug-check -m '[{"name":"warfarin","dose":"5mg","route":"PO"},{"name":"aspirin","dose":"81mg","route":"PO"}]'
    """
    logger = ctx.obj["logger"]

    try:
        # Parse JSON input
        medications_data = json.loads(medications)

        # Validate that it's a list
        if not isinstance(medications_data, list):
            click.echo("Error: --medications must be a JSON array", err=True)
            sys.exit(1)

        # Create MedicationInput objects
        med_objects = []
        for med_data in medications_data:
            try:
                med = MedicationInput(**med_data)
                med_objects.append(med)
            except Exception as e:
                click.echo(f"Error: Invalid medication data: {e}", err=True)
                sys.exit(1)

        # Initialize checker and run check
        checker = DrugInteractionChecker()
        alerts = checker.check_interactions(med_objects, user_id=user_id)

        # Output results as JSON
        output = [alert.model_dump() for alert in alerts]
        click.echo(json.dumps(output, indent=2))

        logger.info(f"Drug interaction check completed: {len(alerts)} alerts found")

    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON format: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.error(f"Drug check failed: {e}")
        sys.exit(1)


@main.command("diagnose")
@click.option("--observations", "-o", required=True, help="JSON observation bundle with vitals, labs, and history")
@click.option("--ruleset", "-r", required=True, help="Name of diagnostic rule set (e.g., 'sepsis_sirs')")
@click.option("--user-id", "-u", default="cli-user", help="User ID for audit logging")
@click.pass_context
def diagnose(ctx, observations, ruleset, user_id):
    """Evaluate clinical observations against diagnostic criteria.

    Example:
        mcp-healthcare diagnose -o '{"vitals":{"temperature":39.0,"heart_rate":110},"labs":{"lactate":4.0},"history":[]}' -r sepsis_sirs
    """
    logger = ctx.obj["logger"]

    try:
        # Parse JSON input
        obs_data = json.loads(observations)

        # Validate that it's a dict with required keys
        if not isinstance(obs_data, dict):
            click.echo("Error: --observations must be a JSON object", err=True)
            sys.exit(1)

        # Create ObservationBundle object
        try:
            obs_bundle = ObservationBundle(**obs_data)
        except Exception as e:
            click.echo(f"Error: Invalid observation data: {e}", err=True)
            sys.exit(1)

        # Initialize evaluator and run evaluation
        evaluator = DiagnosticEvaluator()
        result = evaluator.evaluate(obs_bundle, ruleset, user_id=user_id)

        # Output results as JSON
        click.echo(json.dumps(result, indent=2))

        logger.info(f"Diagnostic evaluation completed: passed={result['passed']}")

    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON format: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.error(f"Diagnostic evaluation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
