"""Database connection and session management."""

import logging
import os
from contextlib import contextmanager
from typing import Generator, Optional

import pymysql
from dotenv import load_dotenv
from python_dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from .models import Base

# Load environment variables from .env if present
load_dotenv()

# Map environment to prefix
ENVIRONMENT = os.getenv("ENVIRONMENT", "DEV").upper()

DB_CONFIGS = {
    "DEV": {
        "host": os.getenv("DEV_DB_HOST", "localhost"),
        "port": int(os.getenv("DEV_DB_PORT", 3306)),
        "user": os.getenv("DEV_DB_USER", "fantasy_user"),
        "password": os.getenv("DEV_DB_PASSWORD", "fantasy_password"),
        "database": os.getenv("DEV_DB_NAME", "fantasy_football_dev"),
    },
    "TEST": {
        "host": os.getenv("TEST_DB_HOST", "localhost"),
        "port": int(os.getenv("TEST_DB_PORT", 3306)),
        "user": os.getenv("TEST_DB_USER", "fantasy_user"),
        "password": os.getenv("TEST_DB_PASSWORD", "fantasy_password"),
        "database": os.getenv("TEST_DB_NAME", "fantasy_football_test"),
    },
    "PRODUCTION": {
        "host": os.getenv("PROD_DB_HOST", "prod-db-host"),
        "port": int(os.getenv("PROD_DB_PORT", 3306)),
        "user": os.getenv("PROD_DB_USER", "prod_user"),
        "password": os.getenv("PROD_DB_PASSWORD", "prod_password"),
        "database": os.getenv("PROD_DB_NAME", "fantasy_football_prod"),
    },
}


def get_db_config():
    env = ENVIRONMENT
    if env not in DB_CONFIGS:
        raise ValueError(
            f"Unknown ENVIRONMENT: {env}. Must be one of {list(DB_CONFIGS.keys())}"
        )
    return DB_CONFIGS[env]


class DatabaseConnection:
    def __init__(self):
        self.config = get_db_config()
        self.connection = None

    def get_connection(self):
        if self.connection is None or not self.connection.open:
            self.connection = pymysql.connect(
                host=self.config["host"],
                port=self.config["port"],
                user=self.config["user"],
                password=self.config["password"],
                database=self.config["database"],
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,
            )
        return self.connection

    def close(self):
        if self.connection and self.connection.open:
            self.connection.close()
            self.connection = None


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or self._get_database_url()
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None

    def _get_database_url(self) -> str:
        """Get database URL from environment variables."""
        # Try environment variables first
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return db_url

        # Build from individual components
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "3306")
        db_user = os.getenv("DB_USER", "fantasy_user")
        db_password = os.getenv("DB_PASSWORD", "fantasy_password")
        db_name = os.getenv("DB_NAME", "fantasy_football")

        return f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"

    def initialize(self) -> None:
        """Initialize database engine and session factory."""
        if self.engine is None:
            self.engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=os.getenv("DB_ECHO", "false").lower() == "true",
            )

            self.SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )

            logger.info("Database connection initialized")

    def create_tables(self) -> None:
        """Create all database tables."""
        if self.engine is None:
            self.initialize()

        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created")

    def drop_tables(self) -> None:
        """Drop all database tables."""
        if self.engine is None:
            self.initialize()

        Base.metadata.drop_all(bind=self.engine)
        logger.info("Database tables dropped")

    def get_session(self) -> Session:
        """Get a new database session."""
        if self.SessionLocal is None:
            self.initialize()

        return self.SessionLocal()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around database operations."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            if self.engine is None:
                self.initialize()

            with self.engine.connect() as connection:
                connection.execute("SELECT 1")

            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def close(self) -> None:
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")


# Global database manager instance
_db_manager = DatabaseManager()


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    return _db_manager


def initialize_database(database_url: Optional[str] = None) -> None:
    """Initialize the global database manager."""
    global _db_manager
    if database_url:
        _db_manager = DatabaseManager(database_url)
    _db_manager.initialize()


def get_session() -> Session:
    """Get a new database session from the global manager."""
    return _db_manager.get_session()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Get a transactional session scope from the global manager."""
    with _db_manager.session_scope() as session:
        yield session


def create_tables() -> None:
    """Create all database tables using the global manager."""
    _db_manager.create_tables()


def test_connection() -> bool:
    """Test database connection using the global manager."""
    return _db_manager.test_connection()
