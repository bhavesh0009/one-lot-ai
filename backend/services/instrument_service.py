import json
import logging
import duckdb
import requests
import os
from pathlib import Path
from datetime import datetime, date

logger = logging.getLogger(__name__)

INSTRUMENT_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
INSTRUMENT_DB_PATH = "instruments.duckdb" # Storing separate from stock data for now, or could use :memory:

class InstrumentService:
    def __init__(self):
        self.db_path = INSTRUMENT_DB_PATH
        self.conn = None
        self._initialize_db()

    def _initialize_db(self):
        """Initialize DuckDB and load data if not present."""
        self.conn = duckdb.connect(self.db_path)
        
        # Check if table exists
        try:
            self.conn.execute("SELECT 1 FROM instruments LIMIT 1")
            count = self.conn.execute("SELECT COUNT(*) FROM instruments").fetchone()[0]
            if count == 0:
                self._load_data()
        except duckdb.CatalogException:
            self._load_data()

    def _load_data(self):
        """Download and load instrument master data."""
        logger.info("Downloading Instrument Master...")
        try:
            response = requests.get(INSTRUMENT_URL, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Loaded {len(data)} instruments from URL. Inserting into DuckDB...")
            
            # Create table
            self.conn.execute("DROP TABLE IF EXISTS instruments")
            self.conn.execute("""
                CREATE TABLE instruments (
                    token VARCHAR,
                    symbol VARCHAR,
                    name VARCHAR,
                    expiry VARCHAR,
                    strike DOUBLE,
                    lotsize VARCHAR,
                    instrumenttype VARCHAR,
                    exch_seg VARCHAR,
                    tick_size VARCHAR
                )
            """)
            
            # Insert data (using DuckDB's JSON capabilities or executemany)
            # Efficient way: Save to temp JSON file and load
            temp_json = "temp_instruments.json"
            with open(temp_json, 'w') as f:
                json.dump(data, f)
            
            self.conn.execute(f"INSERT INTO instruments SELECT * FROM read_json_auto('{temp_json}')")
            os.remove(temp_json)
            
            logger.info("Instrument Master loaded successfully.")
            
        except Exception as e:
            logger.error(f"Failed to load instrument master: {e}")
            # Don't raise - let the server start without instrument data

    def get_token(self, symbol: str, exch_seg: str = "NSE"):
        """Get token for a given symbol (Equity)."""
        # Note: Scrip master format for Equity usually has symbol like 'RELIANCE-EQ'
        query = """
            SELECT token, symbol, name 
            FROM instruments 
            WHERE name = ? AND exch_seg = ? AND instrumenttype = ''
            LIMIT 1
        """
        # Try exact match on 'name' which is usually the ticker like "RELIANCE"
        result = self.conn.execute(query, [symbol, exch_seg]).fetchone()
        if not result:
             # Try adding -EQ suffix if missing
             if exch_seg == "NSE" and not symbol.endswith("-EQ"):
                 result = self.conn.execute(query, [symbol + "-EQ", exch_seg]).fetchone()
        
        return result

    def get_option_symbols(self, symbol: str, expiry: str = None, strike_range: int = 10, atm_strike: float = None):
        """
        Get Option tokens for a stock.
        symbol: Underlying symbol e.g. 'RELIANCE'
        strike_range: Number of strikes above/below ATM to fetch
        atm_strike: Current ATM strike
        """
        # 1. Find nearest expiry if not provided
        # Query: Get distinct expiries for this symbol, sort by date
        # Note: Expiry format in Angel One is text e.g. '28MAR2024'. 
        # We need to parse or string sort? DDMMMYYYY is hard to sort textually.
        # Let's rely on DuckDB's strptime if possible or fetch all and sort in python.
        
        try:
            if not expiry:
                # Fetch all expiries for this symbol's options
                # Assuming symbol name in instruments for options matches underlying?
                # Usually Option Name is like 'RELIANCE28MAR241500CE' but 'name' column might just be 'RELIANCE'
                # Let's check instrumenttype='OPTSTK' and name='RELIANCE'
                
                expiries_query = """
                    SELECT DISTINCT expiry 
                    FROM instruments 
                    WHERE name = ? AND instrumenttype = 'OPTSTK'
                """
                result = self.conn.execute(expiries_query, [symbol]).fetchall()
                expiries = [r[0] for r in result if r[0]]
                
                if not expiries:
                    return []
                
                # Parse dates to find nearest
                # Format: 28MAR2024
                def parse_date(d_str):
                    try:
                        return datetime.strptime(d_str, "%d%b%Y").date()
                    except ValueError:
                        return date.max # Push invalid to end
                
                valid_expiries = sorted(expiries, key=parse_date)
                # Filter for future expiries only? Or just take nearest?
                # If today is expiry, it's valid.
                today = date.today()
                future_expiries = [e for e in valid_expiries if parse_date(e) >= today]
                
                if not future_expiries:
                     return []
                     
                expiry = future_expiries[0] # Nearest expiry
            
            # 2. Get tokens for this expiry
            # If atm_strike is provided, filter by range
            query = """
                SELECT token, symbol, name, expiry, strike, instrumenttype, lotsize
                FROM instruments 
                WHERE name = ? AND expiry = ? AND instrumenttype = 'OPTSTK'
            """
            params = [symbol, expiry]
            
            if atm_strike:
                 # We assume strike step is standard. Hard to guess step.
                 # Just fetch all for expiry and filter in python, or use range
                 # Strike is DECIMAL in DB.
                 # Let's try to get a reasonable buffer. e.g. +/- 5%?
                 # Or just fetch all for that expiry, usually < 100 rows per expiry per stock
                 pass
            
            options = self.conn.execute(query, params).df()
            
            if options.empty:
                return []
                
            # Filter for ATM range in Python
            if atm_strike:
                 # Convert strike to float
                 options['strike'] = options['strike'].astype(float)
                 # Get unique strikes
                 unique_strikes = sorted(options['strike'].unique())
                 
                 # Find index of closest strike to ATM
                 import bisect
                 idx = bisect.bisect_left(unique_strikes, atm_strike)
                 
                 # Define range indices
                 start_idx = max(0, idx - strike_range)
                 end_idx = min(len(unique_strikes), idx + strike_range + 1)
                 
                 target_strikes = unique_strikes[start_idx:end_idx]
                 
                 options = options[options['strike'].isin(target_strikes)]
            
            return options.to_dict(orient="records")

        except Exception as e:
            logger.error(f"Error fetching option symbols: {e}")
            return []
    
    def get_token_by_symbol_name(self, symbol_name: str, exch_seg: str = "NSE"):
        """
        Strict lookup.
        """
        result = self.conn.execute(
            "SELECT token, symbol FROM instruments WHERE symbol = ? AND exch_seg = ?",
            [symbol_name, exch_seg]
        ).fetchone()
        return result if result else None

    def search_instruments(self, query: str, limit: int = 10):
        """
        Search instruments by symbol or name (company name).
        Returns NSE equities only (not derivatives).
        """
        if not query or len(query) < 1:
            return []
        
        try:
            search_term = f"%{query.upper()}%"
            results = self.conn.execute("""
                SELECT DISTINCT name, symbol
                FROM instruments
                WHERE exch_seg = 'NSE'
                  AND instrumenttype = ''
                  AND (UPPER(name) LIKE ? OR UPPER(symbol) LIKE ?)
                ORDER BY 
                    CASE WHEN UPPER(symbol) = ? THEN 0
                         WHEN UPPER(symbol) LIKE ? THEN 1
                         WHEN UPPER(name) LIKE ? THEN 2
                         ELSE 3
                    END,
                    name
                LIMIT ?
            """, [search_term, search_term, query.upper(), f"{query.upper()}%", f"{query.upper()}%", limit]).fetchall()
            
            return [{"symbol": row[0], "name": row[1]} for row in results]
        except Exception as e:
            logger.error(f"Error searching instruments: {e}")
            return []

    def close(self):
        if self.conn:
            self.conn.close()

# Singleton instance - graceful init
try:
    instrument_service = InstrumentService()
except Exception as e:
    logger.error(f"InstrumentService init failed: {e}")
    instrument_service = None
