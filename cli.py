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
from services.database_service import DatabaseService
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
@click.option('--cascade/--no-cascade', default=True,
              help='Automatically include parent tables when syncing dependent tables')
@click.option('--verbose/--no-verbose', default=False,
              help='Show detailed information about skipped records')
def db_sync(direction, tables, output, create_db, cascade, verbose):
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
    
    # Run sync operation using the service
    try:
        results = DatabaseService.sync_databases(direction=direction, tables=tables if tables else None)
    except Exception as e:
        click.echo(f"Error during database synchronization: {str(e)}", err=True)
        return
    
    # Print results summary
    click.echo(f"\nSync completed: {datetime.now().isoformat()}")
    click.echo(f"Direction: {direction}")
    
    if "error" in results:
        click.echo(f"Error: {results['error']}", err=True)
    
    if "database_info" in results:
        click.echo("\nDatabase Information:")
        for key, value in results["database_info"].items():
            click.echo(f"  {key}: {value}")
    
    if "sqlite_to_postgres" in results:
        click.echo("\nSQLite to PostgreSQL:")
        for table, info in results["sqlite_to_postgres"].items():
            status = info.get("status", "unknown")
            if status == "success":
                click.echo(f"  - {table}: {info.get('records', 0)} records in {info.get('time', '?')} " + 
                          f"(created: {info.get('created', 0)}, updated: {info.get('updated', 0)}, " +
                          f"skipped: {info.get('skipped', 0)}, errors: {info.get('errors', 0)})")
                
                # Display skip reasons if verbose and there were skips
                if verbose and info.get('skipped', 0) > 0 and 'skip_reasons' in info:
                    click.echo(f"    Skip reasons:")
                    for reason, count in info['skip_reasons'].items():
                        click.echo(f"      - {reason}: {count}")
            else:
                click.echo(f"  - {table}: {status} - {info.get('message', '')}")
    
    if "postgres_to_sqlite" in results:
        click.echo("\nPostgreSQL to SQLite:")
        for table, info in results["postgres_to_sqlite"].items():
            status = info.get("status", "unknown")
            if status == "success":
                click.echo(f"  - {table}: {info.get('records', 0)} records in {info.get('time', '?')} " + 
                          f"(created: {info.get('created', 0)}, updated: {info.get('updated', 0)}, " +
                          f"skipped: {info.get('skipped', 0)}, errors: {info.get('errors', 0)})")
                
                # Display skip reasons if verbose and there were skips
                if verbose and info.get('skipped', 0) > 0 and 'skip_reasons' in info:
                    click.echo(f"    Skip reasons:")
                    for reason, count in info['skip_reasons'].items():
                        click.echo(f"      - {reason}: {count}")
            else:
                click.echo(f"  - {table}: {status} - {info.get('message', '')}")
    
    # Save results to file if requested
    if output:
        with open(output, 'w') as f:
            json.dump(results, f, indent=2)
        click.echo(f"\nResults saved to {output}")

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

@cli.command('sync-decks')
@click.option('--direction', '-d', 
              type=click.Choice(['sqlite_to_postgres', 'postgres_to_sqlite']),
              default='postgres_to_sqlite', 
              help='Synchronization direction')
@click.option('--deck-id', '-id', type=int, help='Specific deck ID to sync')
def sync_decks(direction, deck_id):
    """Sync flashcard decks and their cards"""
    # This is a specialized command to sync decks and related data
    tables = ['users', 'flashcard_decks', 'flashcards']
    
    click.echo(f"Syncing flashcard decks in {direction} direction...")
    if deck_id:
        click.echo(f"Focusing on deck ID: {deck_id}")
    
    # Use the standard sync function but with deck-related tables
    results = DatabaseService.sync_databases(direction=direction, tables=tables)
    
    # Print a simplified summary
    if direction in results:
        for table, info in results[direction].items():
            status = info.get("status", "unknown")
            if status == "success":
                click.echo(f"{table}: {info.get('records', 0)} records synced " +
                          f"({info.get('skipped', 0)} skipped)")
            else:
                click.echo(f"{table}: {status}")

if __name__ == '__main__':
    cli()
