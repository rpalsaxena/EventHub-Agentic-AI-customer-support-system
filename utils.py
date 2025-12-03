"""
EventHub Utility Functions

Provides helper functions for database operations and model conversions.
Follows the same pattern as CultPass for consistency.
"""

import os
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager


def reset_db(db_path: str, echo: bool = False):
    """
    Drops the existing database file and recreates all tables.

    Args:
        db_path: Path to the SQLite database file (e.g., "data/db/eventhub.db")
        echo: If True, log all SQL statements
    
    Example:
        reset_db("data/db/eventhub.db")
    """
    # Remove the file if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✅ Removed existing {db_path}")

    # Create a new engine and recreate tables
    from data.models import Base

    engine = create_engine(f"sqlite:///{db_path}", echo=echo)
    Base.metadata.create_all(engine)
    print(f"✅ Recreated {db_path} with fresh schema")


@contextmanager
def get_session(engine: Engine):
    """
    Context manager for database sessions with automatic commit/rollback.
    
    Args:
        engine: SQLAlchemy engine instance
    
    Yields:
        session: SQLAlchemy session
    
    Example:
        with get_session(engine) as session:
            user = session.query(User).filter_by(user_id="u_00001").first()
            print(user.full_name)
    """
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def model_to_dict(instance):
    """
    Convert a SQLAlchemy model instance to a dictionary.
    
    Args:
        instance: SQLAlchemy model instance
    
    Returns:
        dict: Dictionary with column names as keys and values as values
    
    Example:
        user = session.query(User).first()
        user_dict = model_to_dict(user)
        # {'user_id': 'u_00001', 'email': 'john@example.com', ...}
    """
    return {
        column.name: getattr(instance, column.name)
        for column in instance.__table__.columns
    }
