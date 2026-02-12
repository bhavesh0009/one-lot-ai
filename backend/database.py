import duckdb
from pathlib import Path

# Hardcoded path to the existing database
DB_PATH = Path("/Users/bhaveshghodasara/Development/price-vol-pattern/data/stocks.duckdb")

def get_db_connection():
    """
    Get a connection to the DuckDB database.
    Using read_only=True to prevent accidental writes since we are just consuming data.
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    
    # Connect in read-only mode
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    return conn
