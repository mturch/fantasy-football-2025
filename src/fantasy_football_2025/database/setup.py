"""Database setup and initialization scripts."""

import os
import sys
import logging
from typing import Optional

from sqlalchemy import text
from python_dotenv import load_dotenv

from .connection import DatabaseManager, get_database_manager
from .models import Base

load_dotenv()

logger = logging.getLogger(__name__)


def create_database_if_not_exists(db_manager: DatabaseManager) -> bool:
    """Create the database if it doesn't exist."""
    try:
        # Parse database URL to get connection details
        db_url = db_manager.database_url
        
        # Extract database name from URL
        if '/' in db_url:
            db_name = db_url.split('/')[-1].split('?')[0]
        else:
            db_name = os.getenv('DB_NAME', 'fantasy_football')
        
        # Create connection URL without database name
        base_url = db_url.rsplit('/', 1)[0]
        
        # Create engine for connection without specific database
        from sqlalchemy import create_engine
        temp_engine = create_engine(base_url)
        
        with temp_engine.connect() as connection:
            # Check if database exists
            result = connection.execute(
                text(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{db_name}'")
            )
            
            if not result.fetchone():
                # Create database
                connection.execute(text(f"CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                logger.info(f"Created database: {db_name}")
            else:
                logger.info(f"Database {db_name} already exists")
        
        temp_engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        return False


def setup_database(database_url: Optional[str] = None, create_db: bool = True) -> bool:
    """Set up the database with all tables and initial data."""
    try:
        # Initialize database manager
        if database_url:
            db_manager = DatabaseManager(database_url)
        else:
            db_manager = get_database_manager()
        
        # Create database if it doesn't exist
        if create_db:
            if not create_database_if_not_exists(db_manager):
                return False
        
        # Initialize connection
        db_manager.initialize()
        
        # Test connection
        if not db_manager.test_connection():
            logger.error("Database connection test failed")
            return False
        
        # Create all tables
        db_manager.create_tables()
        
        logger.info("Database setup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        return False


def reset_database(database_url: Optional[str] = None) -> bool:
    """Reset the database by dropping and recreating all tables."""
    try:
        if database_url:
            db_manager = DatabaseManager(database_url)
        else:
            db_manager = get_database_manager()
        
        db_manager.initialize()
        
        # Drop all tables
        logger.info("Dropping all tables...")
        db_manager.drop_tables()
        
        # Recreate all tables
        logger.info("Creating all tables...")
        db_manager.create_tables()
        
        logger.info("Database reset completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        return False


def create_tables(database_url: Optional[str] = None) -> bool:
    """Create all database tables."""
    try:
        if database_url:
            db_manager = DatabaseManager(database_url)
        else:
            db_manager = get_database_manager()
        
        db_manager.initialize()
        db_manager.create_tables()
        
        logger.info("Tables created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        return False


def verify_database_setup() -> bool:
    """Verify that the database is properly set up."""
    try:
        db_manager = get_database_manager()
        
        # Test connection
        if not db_manager.test_connection():
            logger.error("Database connection failed")
            return False
        
        # Check if tables exist
        with db_manager.session_scope() as session:
            # Try to query a simple table
            from .models import League
            session.query(League).first()
        
        logger.info("Database verification successful")
        return True
        
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        return False


def get_database_info() -> dict:
    """Get information about the current database setup."""
    try:
        db_manager = get_database_manager()
        
        info = {
            'database_url': db_manager.database_url.replace(
                db_manager.database_url.split('://')[1].split('@')[0], '***:***'
            ),  # Hide credentials
            'connection_active': False,
            'tables_exist': False,
            'table_count': 0
        }
        
        if db_manager.test_connection():
            info['connection_active'] = True
            
            with db_manager.session_scope() as session:
                # Count tables
                result = session.execute(
                    text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()")
                )
                info['table_count'] = result.scalar()
                info['tables_exist'] = info['table_count'] > 0
        
        return info
        
    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        return {'error': str(e)}


def main():
    """Main function for CLI database setup."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fantasy Football Database Setup")
    parser.add_argument("--setup", action="store_true", help="Set up the database")
    parser.add_argument("--reset", action="store_true", help="Reset the database")
    parser.add_argument("--verify", action="store_true", help="Verify database setup")
    parser.add_argument("--info", action="store_true", help="Show database info")
    parser.add_argument("--database-url", help="Database URL override")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.setup:
        print("🔧 Setting up database...")
        if setup_database(args.database_url):
            print("✅ Database setup completed successfully")
        else:
            print("❌ Database setup failed")
            sys.exit(1)
    
    elif args.reset:
        print("⚠️  Resetting database (this will delete all data)...")
        confirm = input("Are you sure? Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            if reset_database(args.database_url):
                print("✅ Database reset completed successfully")
            else:
                print("❌ Database reset failed")
                sys.exit(1)
        else:
            print("Database reset cancelled")
    
    elif args.verify:
        print("🔍 Verifying database setup...")
        if verify_database_setup():
            print("✅ Database verification successful")
        else:
            print("❌ Database verification failed")
            sys.exit(1)
    
    elif args.info:
        print("📊 Database Information:")
        info = get_database_info()
        for key, value in info.items():
            print(f"  {key}: {value}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()