
from fastapi import APIRouter, HTTPException, Query
import pandas as pd
import pandas_ta as ta
from database import get_db_connection
from datetime import date, timedelta
import logging
from services.angel_one import angel_service
from services.instrument_service import instrument_service
from services.greeks import compute_greeks, parse_expiry_to_T
from services.news_service import news_service
from services.trade_advisor import trade_advisor
from services.llm_usage import llm_usage_tracker

logger = logging.getLogger(__name__)
router = APIRouter()

# Services are imported as singletons


@router.get("/search")
def search_stocks(q: str = Query("", min_length=1)):
    """
    Search for stocks by symbol or company name.
    Returns top 10 matches from fno_stocks with full company names.
    """
    conn = get_db_connection()
    try:
        search_term = f"%{q.upper()}%"
        results = conn.execute("""
            SELECT symbol, company_name
            FROM fno_stocks
            WHERE UPPER(symbol) LIKE ? OR UPPER(company_name) LIKE ?
            ORDER BY 
                CASE WHEN UPPER(symbol) = ? THEN 0
                     WHEN UPPER(symbol) LIKE ? THEN 1
                     WHEN UPPER(company_name) LIKE ? THEN 2
                     ELSE 3
                END,
                symbol
            LIMIT 10
        """, [search_term, search_term, q.upper(), f"{q.upper()}%", f"{q.upper()}%"]).fetchall()
        
        return {"results": [{"symbol": r[0], "name": r[1]} for r in results]}
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/stock/{ticker}")
def get_stock_info(ticker: str):
    """
    Get basic stock info, ban status, and latest OHLCV (Live from Angel One).
    """
    ticker = ticker.upper()
    conn = get_db_connection()
    try:
        # Basic Info from DB
        basic_info = conn.execute("SELECT * FROM fno_stocks WHERE symbol = ?", [ticker]).fetchone()
        if not basic_info:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        columns = [desc[0] for desc in conn.description]
        basic_data = dict(zip(columns, basic_info))
        
        # Ban Status
        recent_ban = conn.execute("""
            SELECT * FROM fno_ban_period 
            WHERE symbol = ? 
            ORDER BY trade_date DESC 
            LIMIT 1
        """, [ticker]).fetchone()
        
        # Latest Data - Try Angel One Live Price
        live_price = None
        if angel_service:
            try:
                # 1. Get Token
                token_info = instrument_service.get_token(ticker, "NSE")
                if token_info:
                    token = token_info[0] # token
                    # 2. Get LTP
                    ltp_response = angel_service.get_ltp(ticker, token, "NSE")
                    if ltp_response:
                        live_price = ltp_response
            except Exception as e:
                logger.error(f"Error fetching live price: {e}")

        # Fallback to DB if Angel One fails
        latest_ohlcv = conn.execute("""
            SELECT * FROM daily_ohlcv 
            WHERE symbol = ? 
            ORDER BY date DESC 
            LIMIT 1
        """, [ticker]).fetchone()
        
        latest_data = {}
        if latest_ohlcv:
             ohlcv_cols = [desc[0] for desc in conn.description]
             latest_data = dict(zip(ohlcv_cols, latest_ohlcv))
             
             # If live price available, update close
             if live_price:
                 previous_close = latest_data.get('close', 0)
                 latest_data['prev_close'] = previous_close # Shift current close to prev
                 latest_data['close'] = live_price
        
        # Compute change and % change (close vs prev_close)
        close = float(latest_data.get('close', 0))
        prev_close = float(latest_data.get('prev_close', 0))
        change = round(close - prev_close, 2) if prev_close else 0
        change_pct = round((change / prev_close) * 100, 2) if prev_close else 0
        
        return {
            "basic": basic_data,
            "ban_status": recent_ban,
            "latest_ohlcv": latest_data,
            "change": change,
            "change_pct": change_pct
        }
    finally:
        conn.close()

@router.get("/stock/{ticker}/history")
def get_stock_history(ticker: str, days: int = Query(365, description="Number of days of history")):
    """
    Get historical OHLCV data (From DB for now).
    """
    ticker = ticker.upper()
    conn = get_db_connection()
    try:
        cutoff_date = date.today() - timedelta(days=days)
        query = f"""
            SELECT date, open, high, low, close, volume 
            FROM daily_ohlcv 
            WHERE symbol = ? AND date >= ?
            ORDER BY date ASC
        """
        df = conn.execute(query, [ticker, cutoff_date]).df()
        
        if df.empty:
             return []
        
        results = df.to_dict(orient="records")
        return results

    finally:
        conn.close()

@router.get("/stock/{ticker}/technicals")
def get_stock_technicals(ticker: str):
    """
    Calculate and return technical indicators (based on yesterday's data).
    Includes: RSI, MACD, Supertrend, 52W High/Low distance, SMAs, Delivery %
    """
    ticker = ticker.upper()
    conn = get_db_connection()
    try:
        query = """
            SELECT date, open, high, low, close, volume, delivery_pct
            FROM daily_ohlcv 
            WHERE symbol = ?
            ORDER BY date ASC
        """
        df = conn.execute(query, [ticker]).df()
        
        if df.empty:
            raise HTTPException(status_code=404, detail="Not enough data for technicals")

        # --- pandas_ta indicators ---
        # RSI 14
        df.ta.rsi(length=14, append=True)
        # MACD
        df.ta.macd(append=True)
        # Supertrend
        df.ta.supertrend(append=True)
        # SMA 20, 50, 200
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        df.ta.sma(length=200, append=True)
        
        latest = df.iloc[-1]
        close = float(latest['close'])
        
        # --- 52-Week High/Low (252 trading days) ---
        lookback = min(252, len(df))
        recent = df.tail(lookback)
        high_52w = float(recent['high'].max())
        low_52w = float(recent['low'].min())
        dist_52w_high = round(((close - high_52w) / high_52w) * 100, 2) if high_52w else 0
        dist_52w_low = round(((close - low_52w) / low_52w) * 100, 2) if low_52w else 0
        
        # --- Delivery % ---
        delivery_pct = float(latest.get('delivery_pct', 0) or 0)
        # 20-day average delivery %
        last_20 = df.tail(20)['delivery_pct'].dropna()
        avg_delivery_pct = round(float(last_20.mean()), 2) if len(last_20) > 0 else 0
        
        technicals = {
            # Momentum
            "rsi": latest.get("RSI_14"),
            "macd": latest.get("MACD_12_26_9"), 
            "macd_signal": latest.get("MACDs_12_26_9"), 
            "macd_hist": latest.get("MACDh_12_26_9"), 
            "close": close,
            # Trend
            "sma_20": latest.get("SMA_20"),
            "sma_50": latest.get("SMA_50"),
            "sma_200": latest.get("SMA_200"),
            # 52-Week
            "high_52w": high_52w,
            "low_52w": low_52w,
            "dist_52w_high": dist_52w_high,
            "dist_52w_low": dist_52w_low,
            # Volume
            "delivery_pct": delivery_pct,
            "avg_delivery_pct_20": avg_delivery_pct,
        }
        
        st_cols = [c for c in df.columns if c.startswith("SUPERT_")]
        if st_cols:
             technicals["supertrend"] = latest[st_cols[0]]
        
        technicals = {k: (None if pd.isna(v) else round(float(v), 2) if isinstance(v, (float, int)) and v is not None else v) for k, v in technicals.items()}
        
        return technicals
        
    finally:
        conn.close()

@router.get("/stock/{ticker}/chain")
def get_option_chain(ticker: str):
    """
    Get Option Chain for the nearest expiry.
    Returns LTP, OI, Volume, IV, and Greeks for each strike.
    """
    ticker = ticker.upper()
    
    if not angel_service or not instrument_service:
        raise HTTPException(status_code=503, detail="Angel One services not initialized")

    try:
        # 1. Get Underlying LTP (to find ATM)
        token_info = instrument_service.get_token(ticker, "NSE")
        if not token_info:
             raise HTTPException(status_code=404, detail="Stock not found in Master")
        
        token = token_info[0]
        spot_price = angel_service.get_ltp(ticker, token, "NSE")
        
        if not spot_price:
             raise HTTPException(status_code=500, detail="Failed to fetch spot price")

        # 2. Get Option Tokens (Nearest Expiry, ~8 strikes +/-)
        # Angel One stores strikes in paise (×100), so scale spot_price
        atm_paise = spot_price * 100
        options = instrument_service.get_option_symbols(ticker, atm_strike=atm_paise, strike_range=8)
        
        if not options:
             raise HTTPException(status_code=404, detail="No options found")

        expiry = options[0]['expiry'] if options else None

        # 3. BATCH fetch — 1 API call for ALL option prices + OI + volume
        all_tokens = [str(op['token']) for op in options]
        market_data = angel_service.get_market_data_batch(all_tokens, "NFO")

        # 4. Compute time to expiry for Greeks calculation
        T = parse_expiry_to_T(expiry) if expiry else 0

        # 5. Build chain — group CE/PE by strike, compute Greeks locally
        grouped = {}
        for op in options:
            opt_type = "CE" if op['symbol'].endswith("CE") else "PE"
            strike_rupees = op['strike'] / 100.0
            token_str = str(op['token'])
            
            # Get market data for this token
            md = market_data.get(token_str, {})
            ltp = md.get('ltp', 0)
            
            # Compute Greeks locally using Black-Scholes
            greeks = compute_greeks(
                S=spot_price,
                K=strike_rupees,
                T=T,
                option_type=opt_type,
                option_price=ltp
            )
            
            if strike_rupees not in grouped:
                grouped[strike_rupees] = {"strike": strike_rupees}
            
            prefix = "ce" if opt_type == "CE" else "pe"
            grouped[strike_rupees][f'{prefix}Price'] = ltp
            grouped[strike_rupees][f'{prefix}OI'] = md.get('oi', 0)
            grouped[strike_rupees][f'{prefix}Volume'] = md.get('volume', 0)
            grouped[strike_rupees][f'{prefix}Token'] = token_str
            grouped[strike_rupees][f'{prefix}Symbol'] = op['symbol']
            grouped[strike_rupees][f'{prefix}IV'] = greeks['iv']
            grouped[strike_rupees][f'{prefix}Delta'] = greeks['delta']
            grouped[strike_rupees][f'{prefix}Gamma'] = greeks['gamma']
            grouped[strike_rupees][f'{prefix}Theta'] = greeks['theta']
            grouped[strike_rupees][f'{prefix}Vega'] = greeks['vega']
                
        # Sorted by strike
        final_chain = sorted(grouped.values(), key=lambda x: x['strike'])
        
        return {
            "underlying_price": spot_price,
            "expiry": expiry,
            "chain": final_chain
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building option chain: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/news/market")
def get_market_news():
    """
    Get general market news using Gemini Grounded Search.
    """
    return news_service.fetch_news(query="market", type="market")

@router.get("/stock/{ticker}/news")
def get_stock_news(ticker: str):
    """
    Get stock-specific news using Gemini Grounded Search.
    """
    ticker = ticker.upper()
    return news_service.fetch_news(query=ticker, type="stock")

@router.get("/stock/{ticker}/recommendation")
def get_trade_recommendation(ticker: str):
    """
    Get AI-powered trade recommendation using Gemini.
    Analyzes technicals, option chain with Greeks, and news to suggest a trade.
    """
    ticker = ticker.upper()
    try:
        result = trade_advisor.analyze(ticker)
        if result.get("error") and not result.get("recommendation"):
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trade recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/llm/usage")
def get_llm_usage_summary():
    """Get LLM token usage summary (total calls, tokens, cost)."""
    return llm_usage_tracker.get_usage_summary()

@router.get("/llm/usage/recent")
def get_llm_recent_usage(limit: int = Query(20, ge=1, le=100)):
    """Get recent LLM usage records."""
    return llm_usage_tracker.get_recent_usage(limit)

@router.get("/recommendations")
def get_all_recommendations(limit: int = Query(50, ge=1, le=200)):
    """Get all past AI recommendations for forward testing."""
    return llm_usage_tracker.get_recommendations(limit=limit)

@router.get("/stock/{ticker}/recommendations")
def get_stock_recommendations(ticker: str, limit: int = Query(50, ge=1, le=200)):
    """Get past AI recommendations for a specific stock."""
    return llm_usage_tracker.get_recommendations(ticker=ticker.upper(), limit=limit)

