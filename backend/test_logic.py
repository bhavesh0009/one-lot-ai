from database import get_db_connection
import pandas as pd
import pandas_ta as ta

def test_db():
    print("Testing DB connection...")
    try:
        conn = get_db_connection()
        print("Connection successful")
        
        # Check tables
        tables = conn.execute("SHOW TABLES").fetchall()
        print("Tables found:", [t[0] for t in tables])
        
        # Check for a specific stock (e.g. RELIANCE)
        ticker = "RELIANCE"
        
        # Basic info
        basic = conn.execute("SELECT * FROM fno_stocks WHERE symbol = ?", [ticker]).fetchone()
        print(f"Basic Info for {ticker}:", basic)
        
        # OHLCV
        ohlcv = conn.execute("SELECT * FROM daily_ohlcv WHERE symbol = ? ORDER BY date DESC LIMIT 5", [ticker]).df()
        print(f"Latest OHLCV for {ticker}:\n", ohlcv)
        
        if not ohlcv.empty:
            # Technicals calculation test
            print("\nTesting Technicals Calculation...")
            df = conn.execute("SELECT * FROM daily_ohlcv WHERE symbol = ? ORDER BY date ASC", [ticker]).df()
            
            # Ensure date is datetime
            # duckdb returns date as datetime.date usually, pandas need datetime64
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # Calculate RSI
            df.ta.rsi(length=14, append=True)
            print("RSI calculated. Columns:", df.columns[-5:])
            print("Latest RSI:", df.iloc[-1]['RSI_14'])
        else:
            print(f"No OHLCV data found for {ticker}")

    except Exception as e:
        print(f"Test failed with error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    test_db()
