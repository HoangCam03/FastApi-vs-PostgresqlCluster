from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import os

load_dotenv()

# Database URLs for cluster
PRIMARY_DB_URL = os.getenv(
	"PRIMARY_DATABASE_URL",
	"postgresql://blink_user:12345@postgres-primary:5432/blink_db"
)

REPLICA_DB_URL = os.getenv(
	"REPLICA_DATABASE_URL",
	"postgresql://blink_user:12345@postgres-replica-1:5432/blink_db"
)

PGBOUNCER_URL = os.getenv(
	"DATABASE_URL",
	"postgresql://blink_user:12345@pgbouncer:5432/blink_db"
)

# Create engines with connection pooling
def create_engine_with_pooling(url):
	return create_engine(
		url,
		poolclass=QueuePool,
		pool_size=20,
		max_overflow=30,
		pool_pre_ping=True,
		pool_recycle=3600,
		echo=False
	)

# Primary engine for writes
primary_engine = create_engine_with_pooling(PRIMARY_DB_URL)

# Replica engine for reads
replica_engine = create_engine_with_pooling(REPLICA_DB_URL)

# PgBouncer engine for general use
pgbouncer_engine = create_engine_with_pooling(PGBOUNCER_URL)

# Export default engine used by app (for Base.metadata.create_all)
engine = primary_engine

# Session factories
PrimarySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=primary_engine)
ReplicaSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=replica_engine)
PgbouncerSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pgbouncer_engine)

# Base class
Base = declarative_base()

# Dependencies
def get_db():
	"""Get database session from PgBouncer (default)"""
	db = PgbouncerSessionLocal()
	try:
		yield db
	finally:
		db.close()

def get_primary_db():
	"""Get database session from primary node (for writes)"""
	db = PrimarySessionLocal()
	try:
		yield db
	finally:
		db.close()

def get_replica_db():
	"""Get database session from replica node (for reads)"""
	db = ReplicaSessionLocal()
	try:
		yield db
	finally:
		db.close()