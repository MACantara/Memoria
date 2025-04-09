#!/usr/bin/env python
import os
import sys
import click
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from models import db
from config import Config

app = create_app()

@click.group()
def cli():
    """Memoria Command Line Interface"""
    pass

@cli.command('db-sync')
@click.option('--direction', '-d', 
              type=click.Choice(['sqlite_to_postgres', 'postgres_to_sqlite', 'both']),
              default='both', 
              help='Synchronization direction')
@click.option('--tables', '-t', multiple=True, help='Specific tables to sync')
@click.option('--output', '-o', help='Save results to JSON file')
@click.option('--create-db/--no-create-db', default=True, 
              help='Create database and tables if they don\'t exist')
def db_sync(direction, tables, output, create_db):
    """Synchronize SQLite and PostgreSQL databases"""
    # First ensure database directories exist
    Config.ensure_sqlite_directory_exists()
    
    # Show database configuration
    db_type = Config.DB_TYPE
    sqlite_path = Config.SQLITE_DB_PATH
    postgres_url = Config.POSTGRES_URL if Config.POSTGRES_URL else "Not configured"
    
    click.echo(f"Database configuration:")
    click.echo(f"  Active DB: {db_type}")
    click.echo(f"  SQLite path: {sqlite_path}")
    click.echo(f"  SQLite directory exists: {os.path.exists(os.path.dirname(sqlite_path))}")
    click.echo(f"  PostgreSQL URL: {postgres_url.replace(':',':***@') if len(postgres_url) > 20 else postgres_url}")
    
    # Create database tables if requested
    if create_db:
        click.echo("\nEnsuring database tables exist...")
        with app.app_context():
            try:
                db.create_all()
                click.echo("Database tables created successfully.")
            except Exception as e:
                click.echo(f"Error creating database tables: {e}", err=True)
                if click.confirm("Continue with sync anyway?", default=False):
                    click.echo("Continuing with sync operation...")
                else:
                    click.echo("Aborting sync operation.")
                    return
    
    # Import DB sync function only after ensuring directories exist
    try:
        from db_sync import sync_databases
    except Exception as e:
        click.echo(f"Error importing sync module: {e}", err=True)
        sys.exit(1)
    
    click.echo(f"\nStarting database synchronization ({direction})...")
    
    tables_list = list(tables) if tables else None
    
    try:
        results = sync_databases(direction=direction, tables=tables_list)
        
        # Print results summary
        click.echo(f"\nSync completed: {datetime.now().isoformat()}")
        
        if "sqlite_to_postgres" in results:
            click.echo("\nSQLite to PostgreSQL:")
            for table, info in results["sqlite_to_postgres"].items():
                status = info.get("status", "unknown")
                if status == "success":
                    click.echo(f"  - {table}: {info.get('records', 0)} records in {info.get('time', '?')}")
                else:
                    click.echo(f"  - {table}: {status} - {info.get('message', '')}")
        
        if "postgres_to_sqlite" in results:
            click.echo("\nPostgreSQL to SQLite:")
            for table, info in results["postgres_to_sqlite"].items():
                status = info.get("status", "unknown")
                if status == "success":
                    click.echo(f"  - {table}: {info.get('records', 0)} records in {info.get('time', '?')}")
                else:
                    click.echo(f"  - {table}: {status} - {info.get('message', '')}")
        
        # Save results to file if requested
        if output:
            with open(output, 'w') as f:
                json.dump(results, f, indent=2)
            click.echo(f"\nResults saved to {output}")
            
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@cli.command('init-db')
@click.option('--force/--no-force', default=False, help='Force recreation of database tables')
def init_db(force):
    """Initialize the database (creates tables)"""
    # Ensure database directories exist
    Config.ensure_sqlite_directory_exists()
    
    with app.app_context():
        if force:
            click.echo("Dropping all tables...")
            db.drop_all()
        
        click.echo("Creating database tables...")
        db.create_all()
        click.echo("Database initialization complete!")
        click.echo(f"SQLite database path: {Config.SQLITE_DB_PATH}")

if __name__ == '__main__':
    cli()
