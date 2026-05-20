import urllib.parse
import ssl
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import config

# URL-encode password in case of special characters
encoded_password = urllib.parse.quote_plus(config.DB_PASSWORD)

DATABASE_URL = f"mysql+pymysql://{config.DB_USER}:{encoded_password}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"

# Build connect_args for SSL if required (Aiven, PlanetScale, etc.)
connect_args = {}
if config.DB_HOST and "aivencloud" in config.DB_HOST:
    # Aiven MySQL requires SSL. PyMySQL uses ssl dict for this.
    connect_args["ssl"] = {"ssl_mode": "REQUIRED"}

try:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args=connect_args
    )
    # Test connection to trigger exception if MySQL is unavailable
    with engine.connect() as conn:
        pass
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    print("✓ Connected to MySQL database successfully.")
except Exception as e:
    print(f"Database connection failed: {e}")
    print("Falling back to SQLite database.")
    fallback_url = "sqlite:///./fallback_event_db.db"
    engine = create_engine(fallback_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
