"""
Database service for Memoria application.
Handles database initialization, synchronization, and other database operations.
"""

import os
import logging
import json
import time
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, scoped_session
from config import Config
from models import db
from models import (
    User, 
    FlashcardDecks, 
    Flashcards, 
    FlashcardGenerator,
    LearningSession, 
    LearningSection, 
    LearningQuestion,
    ImportFile, 
    ImportChunk, 
    ImportFlashcard, 
    ImportTask
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("database_service")

class DatabaseService:
    """Service for database operations including initialization and synchronization"""
    
    @staticmethod
    def init_db(app):
        """Initialize the database with the application"""
        db.init_app(app)
        
        # Create tables if they don't exist
        with app.app_context():
            try:
                db.create_all()
                logger.info("Database tables created successfully.")
            except Exception as e:
                logger.error(f"Error creating database tables: {e}")
                if "sqlite3.OperationalError" in str(e) and "unable to open database file" in str(e):
                    db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
                    logger.error(f"SQLite database path: {db_path}")
                    logger.error(f"Directory exists: {os.path.exists(os.path.dirname(db_path) if os.path.dirname(db_path) else '.')}")
                    logger.error(f"Directory is writable: {os.access(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', os.W_OK)}")
    
    @staticmethod
    def ensure_directories():
        """Ensure all necessary directories exist"""
        Config.ensure_sqlite_directory_exists()
    
    @staticmethod
    def sync_databases(direction="both", tables=None):
        """
        Synchronize data between SQLite and PostgreSQL databases
        
        Args:
            direction: 'sqlite_to_postgres', 'postgres_to_sqlite', or 'both'
            tables: List of table names to sync (None for all mappable tables)
        
        Returns:
            Dictionary with sync results
        """
        # Ensure directories exist
        DatabaseService.ensure_directories()
        
        config = Config()
        sqlite_uri = f"sqlite:///{config.SQLITE_DB_PATH}"
        postgres_uri = config.POSTGRES_URL
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "direction": direction,
            "tables": tables,
        }
        
        if not postgres_uri:
            error = "PostgreSQL connection string not configured"
            logger.error(error)
            return {"error": error, **results}
            
        # Add database path information to results
        results["database_info"] = {
            "sqlite_path": config.SQLITE_DB_PATH,
            "sqlite_exists": os.path.exists(config.SQLITE_DB_PATH),
            "sqlite_dir_exists": os.path.exists(os.path.dirname(config.SQLITE_DB_PATH)),
            "postgres_url": postgres_uri.split('@')[0] + '@' + postgres_uri.split('@')[1].split('/')[0] + '/***' 
                if '@' in postgres_uri else "Invalid format"
        }
        
        try:
            # Create necessary directories
            sqlite_dir = os.path.dirname(config.SQLITE_DB_PATH)
            if not os.path.exists(sqlite_dir):
                os.makedirs(sqlite_dir, exist_ok=True)
                logger.info(f"Created directory for SQLite database: {sqlite_dir}")
            
            if direction in ["sqlite_to_postgres", "both"]:
                logger.info("Syncing SQLite to PostgreSQL")
                sqlite_to_postgres = DatabaseSyncHelper(
                    source_uri=sqlite_uri,
                    target_uri=postgres_uri,
                    tables=tables
                )
                results["sqlite_to_postgres"] = sqlite_to_postgres.sync_all_tables()
            
            if direction in ["postgres_to_sqlite", "both"]:
                logger.info("Syncing PostgreSQL to SQLite")
                postgres_to_sqlite = DatabaseSyncHelper(
                    source_uri=postgres_uri,
                    target_uri=sqlite_uri,
                    tables=tables
                )
                results["postgres_to_sqlite"] = postgres_to_sqlite.sync_all_tables()
            
            return results
        
        except Exception as e:
            logger.error(f"Sync error: {str(e)}")
            results["error"] = str(e)
            return results
    
    @staticmethod
    def sync_from_supabase_to_sqlite(tables=None):
        """
        Synchronize data from Supabase/PostgreSQL to SQLite
        
        Args:
            tables: List of table names to sync (None for all mappable tables)
        
        Returns:
            Dictionary with sync results
        """
        logger.info("Starting sync from Supabase to SQLite...")
        return DatabaseService.sync_databases(direction="postgres_to_sqlite", tables=tables)


class DatabaseSyncHelper:
    """Helper class for database synchronization between SQLite and PostgreSQL"""
    
    def __init__(self, source_uri, target_uri, tables=None, batch_size=100):
        """
        Initialize the database sync utility
        
        Args:
            source_uri: SQLAlchemy URI for the source database
            target_uri: SQLAlchemy URI for the target database  
            tables: List of table names to sync (None for all tables)
            batch_size: Number of records to process in each batch
        """
        self.source_uri = source_uri
        self.target_uri = target_uri
        self.tables = tables
        self.batch_size = batch_size
        self.source_engine = create_engine(source_uri)
        self.target_engine = create_engine(target_uri)
        
        # Create session factories
        self.SourceSession = scoped_session(sessionmaker(bind=self.source_engine))
        self.TargetSession = scoped_session(sessionmaker(bind=self.target_engine))
        
        # Map model classes to table names - include all models
        self.model_map = {
            'users': User, 
            'flashcard_decks': FlashcardDecks,
            'flashcards': Flashcards,
            'learning_sessions': LearningSession, 
            'learning_sections': LearningSection, 
            'learning_questions': LearningQuestion,
            'import_files': ImportFile, 
            'import_chunks': ImportChunk, 
            'import_flashcards': ImportFlashcard, 
            'import_tasks': ImportTask
        }
        
        # Define table dependencies for foreign key constraints
        # Format: 'table_name': ['dependent_table1', 'dependent_table2', ...]
        self.table_dependencies = {
            'users': [],  # users have no dependencies
            'flashcard_decks': ['users'],  # decks depend on users
            'flashcards': ['flashcard_decks'],  # flashcards depend on decks
            'learning_sessions': ['users'],  
            'learning_sections': ['learning_sessions'],
            'learning_questions': ['learning_sections'],
            'import_files': ['users', 'flashcard_decks'],  # import_files depend on users AND decks
            'import_chunks': ['import_files'],
            'import_flashcards': ['import_chunks'],
            'import_tasks': ['users', 'import_files']
        }
        
        # Cache of primary keys for each table to ensure foreign keys exist
        self.primary_key_cache = {}
        self.foreign_key_columns = {}
        
        # Track failed records to avoid repetitive errors
        self.failed_ids_by_table = {}
    
    @contextmanager
    def source_session(self):
        """Context manager for source database session"""
        session = self.SourceSession()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    @contextmanager
    def target_session(self):
        """Context manager for target database session with error handling"""
        session = self.TargetSession()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.warning(f"Session error (rolling back): {str(e)}")
            # Re-raise the exception for the caller to handle
            raise e
        finally:
            session.close()
    
    def _disable_foreign_keys(self, session):
        """Disable foreign key constraints in a database-specific way"""
        try:
            if 'sqlite' in self.target_uri.lower():
                session.execute(text("PRAGMA foreign_keys = OFF"))
                logger.debug("Disabled SQLite foreign keys")
            elif 'postgresql' in self.target_uri.lower() or 'postgres' in self.target_uri.lower():
                # In PostgreSQL we can't disable constraints for a session without superuser privileges
                # We'll handle this by skipping records that violate constraints instead
                pass
        except Exception as e:
            logger.warning(f"Could not disable foreign keys: {str(e)}")
    
    def _enable_foreign_keys(self, session):
        """Re-enable foreign key constraints in a database-specific way"""
        try:
            if 'sqlite' in self.target_uri.lower():
                session.execute(text("PRAGMA foreign_keys = ON"))
                logger.debug("Re-enabled SQLite foreign keys")
            elif 'postgresql' in self.target_uri.lower() or 'postgres' in self.target_uri.lower():
                # Nothing to do for PostgreSQL as we didn't disable constraints
                pass
        except Exception as e:
            logger.warning(f"Could not re-enable foreign keys: {str(e)}")
    
    def get_all_table_names(self):
        """Get all table names from the source database"""
        inspector = inspect(self.source_engine)
        return inspector.get_table_names()

    def _get_foreign_key_columns(self, table_name):
        """Get all foreign key columns for a table"""
        if table_name in self.foreign_key_columns:
            return self.foreign_key_columns[table_name]
            
        inspector = inspect(self.target_engine)
        fk_columns = {}
        
        try:
            for fk in inspector.get_foreign_keys(table_name):
                for local_col in fk['constrained_columns']:
                    # Map the local column to the referenced table
                    fk_columns[local_col] = fk['referred_table']
        except Exception as e:
            logger.warning(f"Error getting foreign keys for {table_name}: {e}")
            
        self.foreign_key_columns[table_name] = fk_columns
        return fk_columns
    
    def _get_primary_key_columns(self, table_name):
        """Get primary key column names for a table"""
        inspector = inspect(self.source_engine)
        pk_constraint = inspector.get_pk_constraint(table_name)
        
        # Handle different database drivers returning different formats
        if 'constrained_columns' in pk_constraint:
            # SQLAlchemy 1.4+ standard format
            return pk_constraint['constrained_columns']
        elif isinstance(pk_constraint, dict) and 'name' in pk_constraint:
            # Some drivers return a dict with column names in a different key
            for key in ['columns', 'column_names', 'cols']:
                if key in pk_constraint:
                    return pk_constraint[key]
            
        # Fallback: use model's primary key
        model_class = self._get_model_class(table_name)
        if model_class:
            primary_keys = [key.name for key in inspect(model_class).primary_key]
            if primary_keys:
                logger.debug(f"Using model class primary keys for {table_name}: {primary_keys}")
                return primary_keys
                
        logger.warning(f"No primary key found for table {table_name}")
        return []
    
    def _get_model_class(self, table_name):
        """Get the SQLAlchemy model class for a table name"""
        return self.model_map.get(table_name)
    
    def _build_dependency_order(self):
        """Build a list of tables in dependency order"""
        # Start with all tables
        if not self.tables:
            all_tables = list(self.model_map.keys())
        else:
            all_tables = self.tables
        
        # Create a dependency graph for topological sort
        graph = {table: set(self.table_dependencies.get(table, [])) & set(all_tables) 
                 for table in all_tables}
        
        # Perform topological sort to determine sync order
        result = []
        visited = set()
        temp_visited = set()
        
        def visit(node):
            if node in temp_visited:
                logger.warning(f"Circular dependency detected involving {node}")
                return
            if node in visited:
                return
            
            temp_visited.add(node)
            
            for dependency in graph.get(node, set()):
                visit(dependency)
                
            temp_visited.remove(node)
            visited.add(node)
            result.append(node)
            
        for node in all_tables:
            if node not in visited:
                visit(node)
                
        return result
        
    def _cache_primary_keys(self, session, model_class, table_name):
        """Cache primary keys for a table to check foreign key integrity"""
        try:
            pk_cols = self._get_primary_key_columns(table_name)
            if not pk_cols:
                return {}
                
            primary_key = pk_cols[0]  # Assume first PK column for caching
            records = session.query(getattr(model_class, primary_key)).all()
            self.primary_key_cache[table_name] = {r[0] for r in records if r[0] is not None}
            logger.debug(f"Cached {len(self.primary_key_cache[table_name])} keys for {table_name}")
            return self.primary_key_cache[table_name]
        except Exception as e:
            logger.error(f"Error caching primary keys for {table_name}: {str(e)}")
            return {}
            
    def _check_foreign_keys(self, data, table_name):
        """Check and fix foreign key references in a record"""
        fixed_data = data.copy()
        
        # Get record ID for better logging
        pk_cols = self._get_primary_key_columns(table_name)
        record_id = data.get(pk_cols[0]) if pk_cols else None
        
        # First check explicit dependencies from our mapping
        dependencies = self.table_dependencies.get(table_name, [])
        
        for dep_table in dependencies:
            # Find foreign key column (usually dep_table_id)
            fk_column = f"{dep_table[:-1]}_id"  # Remove trailing 's' and add '_id'
            
            if fk_column in fixed_data and fixed_data[fk_column] is not None:
                # Check if the foreign key exists in the target database
                if dep_table in self.primary_key_cache and fixed_data[fk_column] not in self.primary_key_cache[dep_table]:
                    logger.info(f"Skipping {table_name} (id={record_id}): Foreign key violation - {fk_column}={fixed_data[fk_column]} not found in {dep_table}")
                    return None, f"Missing dependency: {dep_table} with id={fixed_data[fk_column]}"
        
        # Now check all foreign keys reported by the database
        fk_columns = self._get_foreign_key_columns(table_name)
        
        for column, referred_table in fk_columns.items():
            if column in fixed_data and fixed_data[column] is not None:
                # Check if the referenced table's primary keys are cached
                if referred_table not in self.primary_key_cache:
                    # Try to load the primary keys for this table
                    if referred_table in self.model_map:
                        with self.target_session() as target_session:
                            self._cache_primary_keys(target_session, self.model_map[referred_table], referred_table)
                
                # Now check if the foreign key exists
                if referred_table in self.primary_key_cache and fixed_data[column] not in self.primary_key_cache[referred_table]:
                    logger.info(f"Skipping {table_name} (id={record_id}): Foreign key violation - {column}={fixed_data[column]} not found in {referred_table}")
                    return None, f"Missing reference: {referred_table} with id={fixed_data[column]}"
                    
        return fixed_data, None
    
    def _track_failed_record(self, table_name, record_id, reason=None):
        """Track a failed record to avoid repeated attempts"""
        if table_name not in self.failed_ids_by_table:
            self.failed_ids_by_table[table_name] = {}
            
        self.failed_ids_by_table[table_name][record_id] = reason or "Unknown error"
        
    def _is_failed_record(self, table_name, record_id):
        """Check if a record has already failed in this sync operation"""
        return table_name in self.failed_ids_by_table and record_id in self.failed_ids_by_table[table_name]
    
    def _get_failed_reason(self, table_name, record_id):
        """Get the reason a record failed in a previous attempt"""
        if table_name in self.failed_ids_by_table and record_id in self.failed_ids_by_table[table_name]:
            return self.failed_ids_by_table[table_name][record_id]
        return "Unknown reason"
    
    def sync_table(self, table_name):
        """Synchronize a single table from source to target"""
        logger.info(f"Syncing table: {table_name}")
        model_class = self._get_model_class(table_name)
        
        if not model_class:
            logger.warning(f"No model class found for table '{table_name}', skipping")
            return {"status": "skipped", "reason": "No model mapping"}

        # Get primary key columns
        pk_cols = self._get_primary_key_columns(table_name)
        if not pk_cols:
            logger.warning(f"No primary key found for table '{table_name}', skipping")
            return {"status": "skipped", "reason": "No primary key"}
            
        logger.debug(f"Primary key columns for {table_name}: {pk_cols}")
        
        try:
            # Create target table if it doesn't exist
            model_class.__table__.create(bind=self.target_engine, checkfirst=True)
            logger.info(f"Ensured target table '{table_name}' exists")
            
            # Cache existing primary keys in target database
            with self.target_session() as target_session:
                self._cache_primary_keys(target_session, model_class, table_name)
                
            # Pre-cache primary keys of dependency tables to validate foreign keys
            for dep_table in self.table_dependencies.get(table_name, []):
                if dep_table not in self.primary_key_cache:
                    dep_model = self._get_model_class(dep_table)
                    if dep_model:
                        with self.target_session() as target_session:
                            self._cache_primary_keys(target_session, dep_model, dep_table)
                    
        except Exception as e:
            logger.warning(f"Error preparing table '{table_name}': {str(e)}")
            return {"status": "error", "message": str(e), "records": 0}
            
        # Process records in batches
        offset = 0
        total_synced = 0
        errors = 0
        skipped = 0
        created = 0
        updated = 0
        batch_errors = 0
        skip_reasons = {}
        
        while True:
            try:
                batch_errors = 0  # Reset batch error counter
                with self.source_session() as source_session:
                    # Get batch of records from source
                    query = source_session.query(model_class)
                    records = query.limit(self.batch_size).offset(offset).all()
                    
                    if not records:
                        break
                    
                    batch_size = len(records)
                    logger.debug(f"Processing batch of {batch_size} records from offset {offset}")
                    
                    # Process records with a clean session for each record to prevent cascading failures
                    for record_idx, record in enumerate(records):
                        # Create a dictionary of the record's attributes
                        data = {c.name: getattr(record, c.name) 
                                for c in record.__table__.columns}
                                
                        # Get primary key for tracking failures
                        record_id = None
                        if pk_cols:
                            record_id = data.get(pk_cols[0])
                        
                        # Skip if this record has failed before
                        if record_id is not None and self._is_failed_record(table_name, record_id):
                            reason = self._get_failed_reason(table_name, record_id)
                            logger.debug(f"Skipping previously failed record {table_name} (id={record_id}): {reason}")
                            skipped += 1
                            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                            continue
                            
                        try:
                            # Start a fresh session for each record to avoid transaction failures affecting multiple records
                            with self.target_session() as target_session:
                                # Use database-specific method to disable foreign keys
                                self._disable_foreign_keys(target_session)

                                # Check foreign key constraints
                                checked_data, skip_reason = self._check_foreign_keys(data, table_name)
                                if checked_data is None:
                                    # Skip this record due to FK constraint issues
                                    if record_id is not None:
                                        self._track_failed_record(table_name, record_id, skip_reason)
                                    skipped += 1
                                    skip_reasons[skip_reason] = skip_reasons.get(skip_reason, 0) + 1
                                    continue
                                
                                # Check if record exists in target
                                pk_filter = {}
                                for pk in pk_cols:
                                    if pk in checked_data:
                                        pk_filter[pk] = checked_data[pk]
                                    else:
                                        logger.warning(f"Primary key {pk} not found in record data for {table_name}")
                                        
                                if not pk_filter:
                                    skip_reason = "Missing primary key values"
                                    logger.warning(f"No primary key values found for record in {table_name}, skipping")
                                    skipped += 1
                                    skip_reasons[skip_reason] = skip_reasons.get(skip_reason, 0) + 1
                                    if record_id is not None:
                                        self._track_failed_record(table_name, record_id, skip_reason)
                                    continue
                                    
                                existing = target_session.query(model_class).filter_by(**pk_filter).first()
                                
                                if existing:
                                    # Update existing record
                                    for key, value in checked_data.items():
                                        setattr(existing, key, value)
                                    
                                    # Update the primary key cache
                                    for pk in pk_cols:
                                        if pk in checked_data and checked_data[pk] is not None:
                                            self.primary_key_cache.setdefault(table_name, set()).add(checked_data[pk])
                                    
                                    updated += 1
                                    logger.debug(f"Updated {table_name} record (id={record_id})")
                                else:
                                    # Create new record
                                    new_record = model_class(**checked_data)
                                    target_session.add(new_record)
                                    
                                    # Update the primary key cache
                                    for pk in pk_cols:
                                        if pk in checked_data and checked_data[pk] is not None:
                                            self.primary_key_cache.setdefault(table_name, set()).add(checked_data[pk])
                                    
                                    created += 1
                                    logger.debug(f"Created new {table_name} record (id={record_id})")
                                
                                # Use database-specific method to re-enable foreign keys
                                self._enable_foreign_keys(target_session)
                                
                                # Commit this record's transaction
                                target_session.commit()
                                total_synced += 1
                                logger.debug(f"Transaction successful for {table_name} record (id={record_id})")
                                
                        except Exception as e:
                            # Log the error but continue with next record
                            errors += 1
                            batch_errors += 1
                            error_msg = str(e)
                            if record_id is not None:
                                self._track_failed_record(table_name, record_id, f"Error: {error_msg}")
                            logger.error(f"Error processing record in {table_name} (id={record_id}): {error_msg}")
                            
                            # If we have too many errors in this batch, break out
                            if batch_errors > batch_size / 2:  # If more than 50% of batch failed
                                logger.error(f"Too many errors in this batch ({batch_errors}/{batch_size}), skipping remaining records")
                                break
                    
                    # Move to next batch
                    offset += batch_size
                    logger.info(f"Synced {total_synced} records from {table_name}, created {created}, updated {updated}, skipped {skipped}, errors {errors}")
                    
            except Exception as e:
                logger.error(f"Error processing batch for {table_name} at offset {offset}: {str(e)}")
                offset += self.batch_size  # Skip this batch and try the next one
                errors += 1
                
                # If there are too many consecutive errors, stop processing
                if errors > 5:
                    logger.error(f"Too many errors while syncing {table_name}, stopping")
                    break
        
        # Log skip reasons summary
        if skipped > 0:
            logger.info(f"Skip reasons for {table_name}:")
            for reason, count in skip_reasons.items():
                logger.info(f"  - {reason}: {count} records")
        
        return {
            "status": "success",
            "records": total_synced,
            "created": created,
            "updated": updated,
            "time": f"{time.time() - self._start_time:.2f}s",
            "skipped": skipped,
            "skip_reasons": skip_reasons,
            "errors": errors
        }
    
    def sync_all_tables(self):
        """Synchronize all tables from source to target"""
        # Get tables in dependency order
        ordered_tables = self._build_dependency_order()
        results = {}
        self._start_time = time.time()
        
        for table_name in ordered_tables:
            if table_name in self.model_map:
                table_start_time = time.time()
                try:
                    result = self.sync_table(table_name)
                    elapsed = time.time() - table_start_time
                    
                    if isinstance(result, dict):
                        result["time"] = f"{elapsed:.2f}s"
                        results[table_name] = result
                    else:
                        # If sync_table returned a non-dict value (like an int), create a result dict
                        results[table_name] = {
                            "records": result,
                            "time": f"{elapsed:.2f}s",
                            "status": "success"
                        }
                except Exception as e:
                    logger.error(f"Error syncing {table_name}: {str(e)}")
                    results[table_name] = {
                        "status": "error",
                        "message": str(e)
                    }
            else:
                results[table_name] = {"status": "skipped", "message": "No model mapping"}
        
        return results
