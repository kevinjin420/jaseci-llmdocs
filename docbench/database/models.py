#!/usr/bin/env python3
"""
Database models and schemas for Jaseci Benchmark
All data stored in PostgreSQL with proper JSON schemas
"""

import os
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, Integer, String, Float, Text, Boolean, JSON, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.pool import QueuePool
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()


def get_json_type():
    """Return JSONB for PostgreSQL, JSON for SQLite"""
    db_url = os.getenv('DATABASE_URL', 'sqlite:///./benchmark.db')
    if 'postgresql' in db_url:
        return JSONB
    return JSON


class Collection(Base):
    """Collections for grouping benchmark results"""
    __tablename__ = 'collections'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), unique=True, nullable=False, index=True)

    # Metadata
    description = Column(Text, nullable=True)
    created_at = Column(Float, nullable=False)

    # Relationships
    results = relationship('BenchmarkResult', back_populates='collection_obj')

    __table_args__ = (
        Index('idx_collection_created', created_at.desc()),
    )


class BenchmarkResult(Base):
    """Complete benchmark results with all test responses"""
    __tablename__ = 'benchmark_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(256), unique=True, nullable=False, index=True)

    # Model and variant info
    model = Column(String(256), nullable=False, index=True)
    model_id = Column(String(256), nullable=False)
    variant = Column(String(128), nullable=False, index=True)

    # Run configuration
    temperature = Column(Float, nullable=False)
    max_tokens = Column(Integer, nullable=False)

    # Metadata
    total_tests = Column(Integer, nullable=False)
    batch_size = Column(Integer, nullable=True)
    num_batches = Column(Integer, nullable=True)

    # Results - stored as JSONB for efficient querying
    responses = Column(get_json_type(), nullable=False)  # {test_id: code}
    run_metadata = Column(get_json_type(), nullable=True)

    # Evaluation results (computed after responses saved)
    evaluation_results = Column(get_json_type(), nullable=True)  # Full evaluation with scores
    total_score = Column(Float, nullable=True, index=True)
    max_score = Column(Float, nullable=True)
    percentage = Column(Float, nullable=True, index=True)

    # Timestamps
    created_at = Column(Float, nullable=False, index=True)
    evaluated_at = Column(Float, nullable=True)

    # Status
    status = Column(String(32), nullable=False, default='completed', index=True)
    evaluation_status = Column(String(32), nullable=True, default='pending', index=True)  # pending, evaluating, completed, failed

    # Collection grouping (for organizing multiple runs)
    collection_id = Column(Integer, ForeignKey('collections.id'), nullable=True, index=True)

    # Relationships
    collection_obj = relationship('Collection', back_populates='results')

    __table_args__ = (
        Index('idx_model_variant', 'model', 'variant'),
        Index('idx_created_at_desc', created_at.desc()),
        Index('idx_score_desc', total_score.desc()),
        Index('idx_collection_id', 'collection_id'),
    )


class BenchmarkRun(Base):
    """Benchmark run tracking (in-progress and historical)"""
    __tablename__ = 'benchmark_runs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(256), unique=True, nullable=False, index=True)

    # Model and variant
    model = Column(String(256), nullable=False, index=True)
    model_id = Column(String(256), nullable=False)
    variant = Column(String(128), nullable=False)

    # Configuration
    temperature = Column(Float, nullable=False)
    max_tokens = Column(Integer, nullable=False)

    # Status tracking
    status = Column(String(32), nullable=False, index=True)  # running, completed, failed
    progress = Column(String(512), nullable=True)

    # References
    result_id = Column(Integer, nullable=True)  # FK to benchmark_results.id

    # Timestamps
    started_at = Column(Float, nullable=False, index=True)
    completed_at = Column(Float, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)

    # Additional metadata
    run_metadata = Column(get_json_type(), nullable=True)

    __table_args__ = (
        Index('idx_status_started', 'status', started_at.desc()),
    )


class DocumentationVariant(Base):
    """Documentation variants"""
    __tablename__ = 'documentation_variants'

    id = Column(Integer, primary_key=True, autoincrement=True)
    variant_name = Column(String(128), unique=True, nullable=False, index=True)
    url = Column(String(512), nullable=False)

    # Cached content (fetched from URL)
    content = Column(Text, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    cached_at = Column(Float, nullable=True)
    cache_ttl = Column(Integer, nullable=False, default=3600)

    # Timestamps
    created_at = Column(Float, nullable=False)
    updated_at = Column(Float, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)


# Database connection configuration
def get_database_url() -> str:
    """Get database URL from environment"""
    url = os.getenv('DATABASE_URL')

    if not url:
        # Default to SQLite for local dev
        return 'sqlite:///./benchmark.db'

    return url


# Create engine with connection pooling
def create_db_engine():
    db_url = get_database_url()
    is_postgres = 'postgresql' in db_url

    engine_kwargs = {
        'echo': os.getenv('SQL_ECHO', 'false').lower() == 'true'
    }

    if is_postgres:
        engine_kwargs.update({
            'poolclass': QueuePool,
            'pool_size': int(os.getenv('DB_POOL_SIZE', '10')),
            'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '20')),
            'pool_pre_ping': True,
            'pool_recycle': 3600,
        })

    return create_engine(db_url, **engine_kwargs)

engine = create_db_engine()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Session:
    """Context manager for database sessions"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Initialize database schema"""
    try:
        Base.metadata.create_all(bind=engine)
        print(f"Database initialized successfully ({get_database_url()})")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise


def drop_all_tables():
    """Drop all tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped")


# Initialize database on module import (only if AUTO_INIT_DB is true)
if os.getenv('AUTO_INIT_DB', 'true').lower() == 'true':
    try:
        init_db()
    except Exception as e:
        print(f"Warning: Could not auto-initialize database: {e}")
