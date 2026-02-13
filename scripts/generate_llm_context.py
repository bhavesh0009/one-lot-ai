
import os
import sys
import json
import logging
from datetime import date, datetime
import pandas as pd
import pandas_ta as ta
from dotenv import load_dotenv

# Add backend to sys.path
backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
sys.path.append(backend_path)

from database import get_db_connection
from services.news_service import news_service
from services.angel_one import angel_service
from services.instrument_service import instrument_service
from services.greeks import compute_greeks, parse_expiry_to_T

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env
load_dotenv(os.path.join(backend_path, '.env'))


def _safe(val, fmt=".2f"):
    """Format a numeric value safely, returning 'N/A' for None/NaN."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    return f"{val:{fmt}}"


def _pct_change(current, previous):
    """Calculate percentage change, return None if not possible."""
    if previous is None or previous == 0 or current is None:
        return None
    return ((current - previous) / previous) * 100


def get_stock_data(ticker):
    """
    Fetch full OHLCV dataframe and compute all technicals + historical changes.
    Returns technicals dict or None.
    """
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
            return None

        # --- Technical Indicators ---
        df.ta.rsi(length=14, append=True)
        df.ta.macd(append=True)
        df.ta.supertrend(append=True)
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        df.ta.sma(length=200, append=True)
        df.ta.bbands(length=20, append=True)
        df.ta.ema(length=9, append=True)
        df.ta.ema(length=21, append=True)
        df.ta.atr(length=14, append=True)
        df.ta.adx(length=14, append=True)
        df.ta.stoch(append=True)
        df.ta.cci(length=20, append=True)
        df.ta.willr(length=14, append=True)

        latest = df.iloc[-1]
        close = float(latest['close'])

        def _col(prefix):
            """Find first column starting with prefix."""
            matches = [c for c in df.columns if c.startswith(prefix)]
            return latest[matches[0]] if matches else None

        # --- 52-Week High/Low ---
        lookback = min(252, len(df))
        recent = df.tail(lookback)
        high_52w = float(recent['high'].max())
        low_52w = float(recent['low'].min())

        # --- Historical Change % ---
        def close_n_days_ago(n):
            """Get close price approximately n trading days ago."""
            idx = len(df) - 1 - n
            if idx >= 0:
                return float(df.iloc[idx]['close'])
            return None

        prev_close = close_n_days_ago(1)
        close_7d = close_n_days_ago(5)     # ~5 trading days = 1 week
        close_15d = close_n_days_ago(10)   # ~10 trading days = 2 weeks
        close_1m = close_n_days_ago(22)    # ~22 trading days = 1 month
        close_1y = close_n_days_ago(252)   # ~252 trading days = 1 year

        # --- Supertrend direction ---
        st_dir_cols = [c for c in df.columns if c.startswith("SUPERTd_")]
        st_direction = None
        if st_dir_cols:
            st_val = latest[st_dir_cols[0]]
            st_direction = "Bullish" if st_val == 1 else "Bearish"

        st_cols = [c for c in df.columns if c.startswith("SUPERT_")]
        supertrend_val = float(latest[st_cols[0]]) if st_cols else None

        # --- Delivery % ---
        delivery_pct = float(latest.get('delivery_pct', 0) or 0)
        last_20_del = df.tail(20)['delivery_pct'].dropna()
        avg_delivery_20 = float(last_20_del.mean()) if len(last_20_del) > 0 else 0

        # --- Volume ---
        vol = float(latest.get('volume', 0) or 0)
        avg_vol_20 = float(df.tail(20)['volume'].mean()) if len(df) >= 20 else vol

        technicals = {
            "data_date": str(latest['date']),
            "close": close,
            "prev_close": prev_close,
            # Historical changes
            "change_1d_pct": _pct_change(close, prev_close),
            "change_7d_pct": _pct_change(close, close_7d),
            "change_15d_pct": _pct_change(close, close_15d),
            "change_1m_pct": _pct_change(close, close_1m),
            "change_1y_pct": _pct_change(close, close_1y),
            # Momentum
            "rsi_14": latest.get("RSI_14"),
            "macd": latest.get("MACD_12_26_9"),
            "macd_signal": latest.get("MACDs_12_26_9"),
            "macd_hist": latest.get("MACDh_12_26_9"),
            "stoch_k": latest.get("STOCHk_14_3_3"),
            "stoch_d": latest.get("STOCHd_14_3_3"),
            "cci_20": latest.get("CCI_20_0.015"),
            "willr_14": latest.get("WILLR_14"),
            # Trend
            "sma_20": latest.get("SMA_20"),
            "sma_50": latest.get("SMA_50"),
            "sma_200": latest.get("SMA_200"),
            "ema_9": latest.get("EMA_9"),
            "ema_21": latest.get("EMA_21"),
            "supertrend": supertrend_val,
            "supertrend_direction": st_direction,
            "adx": latest.get("ADX_14"),
            "plus_di": latest.get("DMP_14"),
            "minus_di": latest.get("DMN_14"),
            # Volatility
            "bb_upper": _col("BBU_"),
            "bb_middle": _col("BBM_"),
            "bb_lower": _col("BBL_"),
            "atr_14": _col("ATR"),
            # 52-Week
            "high_52w": high_52w,
            "low_52w": low_52w,
            # Volume
            "volume": vol,
            "avg_volume_20": avg_vol_20,
            "delivery_pct": delivery_pct,
            "avg_delivery_pct_20": avg_delivery_20,
        }

        return technicals
    finally:
        conn.close()


def get_live_price(ticker):
    """Fetch live LTP from Angel One. Returns ltp or None."""
    if not angel_service or not instrument_service:
        return None
    try:
        token_info = instrument_service.get_token(ticker, "NSE")
        if not token_info:
            return None
        token = token_info[0]
        return angel_service.get_ltp(ticker, token, "NSE")
    except Exception as e:
        logger.error(f"Error fetching live price: {e}")
        return None


def get_option_chain_with_greeks(ticker, spot_price):
    """
    Build full option chain with Greeks, grouped by strike.
    Returns dict with underlying, expiry, atm_strike, and chain rows.
    """
    if not angel_service or not instrument_service:
        return "Angel One services unavailable."

    try:
        atm_paise = spot_price * 100
        options = instrument_service.get_option_symbols(ticker, atm_strike=atm_paise, strike_range=8)
        if not options:
            return "No options found."

        expiry = options[0]['expiry']
        T = parse_expiry_to_T(expiry) if expiry else 0

        # Batch fetch market data
        all_tokens = [str(op['token']) for op in options]
        market_data = angel_service.get_market_data_batch(all_tokens, "NFO")

        # Get lot size from first option
        lot_size = options[0].get('lotsize', 'N/A')

        # Group by strike: {strike: {ce: {...}, pe: {...}}}
        grouped = {}
        for op in options:
            opt_type = "CE" if op['symbol'].endswith("CE") else "PE"
            strike = op['strike'] / 100.0
            token_str = str(op['token'])
            md = market_data.get(token_str, {})
            ltp = md.get('ltp', 0)

            # Compute Greeks locally
            greeks = compute_greeks(
                S=spot_price,
                K=strike,
                T=T,
                option_type=opt_type,
                option_price=ltp
            )

            side_data = {
                "price": ltp,
                "oi": md.get('oi', 0),
                "volume": md.get('volume', 0),
                "iv": greeks['iv'],
                "delta": greeks['delta'],
                "gamma": greeks['gamma'],
                "theta": greeks['theta'],
                "vega": greeks['vega'],
            }

            if strike not in grouped:
                grouped[strike] = {"strike": strike, "ce": {}, "pe": {}}
            grouped[strike][opt_type.lower()] = side_data

        # Sort by strike
        chain = sorted(grouped.values(), key=lambda x: x['strike'])

        # Determine ATM strike (closest to spot)
        atm_strike = min(grouped.keys(), key=lambda s: abs(s - spot_price)) if grouped else None

        return {
            "underlying": spot_price,
            "expiry": expiry,
            "days_to_expiry": max(0, (datetime.strptime(expiry, "%d%b%Y").date() - date.today()).days) if expiry else 0,
            "lot_size": lot_size,
            "atm_strike": atm_strike,
            "chain": chain,
        }
    except Exception as e:
        return f"Error fetching chain: {e}"


def generate_markdown(ticker):
    print(f"Generating context for {ticker}...")

    # 1. Historical data + technicals from DB
    print("Computing technicals from DB...")
    tech = get_stock_data(ticker)

    # 2. Live price
    print("Fetching live price...")
    live_ltp = get_live_price(ticker)

    # Determine current price for display and option chain
    if live_ltp:
        current_price = live_ltp
        price_source = "Live (Angel One)"
    elif tech:
        current_price = tech['close']
        price_source = f"Last DB Close ({tech['data_date']})"
    else:
        current_price = None
        price_source = "Unavailable"

    # 3. Option chain with Greeks
    print("Fetching Option Chain with Greeks...")
    chain = None
    if current_price:
        chain = get_option_chain_with_greeks(ticker, current_price)

    # 4. News
    print("Fetching Stock News...")
    stock_news = news_service.fetch_news(ticker, "stock")
    print("Fetching Market News...")
    market_news = news_service.fetch_news("market", "market")

    # ──────────────── FORMAT OUTPUT ────────────────
    now = datetime.now()
    md = f"# Trading Context: {ticker}\n\n"
    md += f"**Generated:** {now.strftime('%A, %d %B %Y at %I:%M %p IST')}\n\n"

    # ── Header: Price Snapshot ──
    md += "## Price Snapshot\n"
    if current_price and tech:
        today_change_pct = _pct_change(current_price, tech.get('prev_close'))
        md += f"| Metric | Value |\n|---|---|\n"
        md += f"| **LTP** | {_safe(current_price)} ({price_source}) |\n"
        md += f"| **Today's Change** | {_safe(today_change_pct)}% |\n"
        md += f"| **Last Day Change** | {_safe(tech.get('change_1d_pct'))}% |\n"
        md += f"| **7-Day Change** | {_safe(tech.get('change_7d_pct'))}% |\n"
        md += f"| **15-Day Change** | {_safe(tech.get('change_15d_pct'))}% |\n"
        md += f"| **1-Month Change** | {_safe(tech.get('change_1m_pct'))}% |\n"
        md += f"| **1-Year Change** | {_safe(tech.get('change_1y_pct'))}% |\n"
        md += f"| **52W High** | {_safe(tech.get('high_52w'))} ({_safe(_pct_change(current_price, tech.get('high_52w')))}% from high) |\n"
        md += f"| **52W Low** | {_safe(tech.get('low_52w'))} ({_safe(_pct_change(current_price, tech.get('low_52w')))}% from low) |\n"
    elif current_price:
        md += f"- **LTP:** {_safe(current_price)} ({price_source})\n"
    else:
        md += "Price data unavailable.\n"
    md += "\n"

    # ── Technical Analysis ──
    md += "## Technical Analysis\n"
    if tech:
        md += f"*Based on DB data through {tech['data_date']}*\n\n"

        # Trend Indicators
        md += "### Trend\n"
        md += f"| Indicator | Value | Signal |\n|---|---|---|\n"

        close = tech['close']
        sma20 = tech.get('sma_20')
        sma50 = tech.get('sma_50')
        sma200 = tech.get('sma_200')
        ema9 = tech.get('ema_9')
        ema21 = tech.get('ema_21')

        def _above_below(price, level):
            if level is None or pd.isna(level):
                return "N/A"
            return "Above" if price > level else "Below"

        md += f"| SMA 20 | {_safe(sma20)} | Price {_above_below(close, sma20)} |\n"
        md += f"| SMA 50 | {_safe(sma50)} | Price {_above_below(close, sma50)} |\n"
        md += f"| SMA 200 | {_safe(sma200)} | Price {_above_below(close, sma200)} |\n"
        md += f"| EMA 9 | {_safe(ema9)} | Price {_above_below(close, ema9)} |\n"
        md += f"| EMA 21 | {_safe(ema21)} | Price {_above_below(close, ema21)} |\n"
        md += f"| Supertrend | {_safe(tech.get('supertrend'))} | {tech.get('supertrend_direction', 'N/A')} |\n"

        adx = tech.get('adx')
        adx_signal = "N/A"
        if adx is not None and not pd.isna(adx):
            if adx > 25:
                adx_signal = "Strong Trend"
            else:
                adx_signal = "Weak/No Trend"
        md += f"| ADX | {_safe(adx)} | {adx_signal} |\n"
        md += f"| +DI / -DI | {_safe(tech.get('plus_di'))} / {_safe(tech.get('minus_di'))} | {'Bullish' if (tech.get('plus_di') or 0) > (tech.get('minus_di') or 0) else 'Bearish'} |\n"
        md += "\n"

        # Momentum Indicators
        md += "### Momentum\n"
        md += f"| Indicator | Value | Signal |\n|---|---|---|\n"

        rsi = tech.get('rsi_14')
        rsi_signal = "N/A"
        if rsi is not None and not pd.isna(rsi):
            if rsi > 70:
                rsi_signal = "Overbought"
            elif rsi < 30:
                rsi_signal = "Oversold"
            else:
                rsi_signal = "Neutral"
        md += f"| RSI (14) | {_safe(rsi)} | {rsi_signal} |\n"

        macd_hist = tech.get('macd_hist')
        macd_signal_text = "N/A"
        if macd_hist is not None and not pd.isna(macd_hist):
            macd_signal_text = "Bullish" if macd_hist > 0 else "Bearish"
        md += f"| MACD | {_safe(tech.get('macd'))} | {macd_signal_text} |\n"
        md += f"| MACD Signal | {_safe(tech.get('macd_signal'))} | |\n"
        md += f"| MACD Histogram | {_safe(macd_hist)} | |\n"

        stoch_k = tech.get('stoch_k')
        stoch_signal = "N/A"
        if stoch_k is not None and not pd.isna(stoch_k):
            if stoch_k > 80:
                stoch_signal = "Overbought"
            elif stoch_k < 20:
                stoch_signal = "Oversold"
            else:
                stoch_signal = "Neutral"
        md += f"| Stochastic %K/%D | {_safe(stoch_k)} / {_safe(tech.get('stoch_d'))} | {stoch_signal} |\n"
        md += f"| CCI (20) | {_safe(tech.get('cci_20'))} | |\n"
        md += f"| Williams %R (14) | {_safe(tech.get('willr_14'))} | |\n"
        md += "\n"

        # Volatility
        md += "### Volatility\n"
        md += f"| Indicator | Value |\n|---|---|\n"
        md += f"| Bollinger Upper | {_safe(tech.get('bb_upper'))} |\n"
        md += f"| Bollinger Middle | {_safe(tech.get('bb_middle'))} |\n"
        md += f"| Bollinger Lower | {_safe(tech.get('bb_lower'))} |\n"

        bb_upper = tech.get('bb_upper')
        bb_lower = tech.get('bb_lower')
        if bb_upper and bb_lower and not pd.isna(bb_upper) and not pd.isna(bb_lower):
            bb_width = ((bb_upper - bb_lower) / tech.get('bb_middle', 1)) * 100
            md += f"| BB Width | {_safe(bb_width)}% |\n"

        md += f"| ATR (14) | {_safe(tech.get('atr_14'))} |\n"
        md += "\n"

        # Volume
        md += "### Volume & Delivery\n"
        md += f"| Metric | Value |\n|---|---|\n"
        md += f"| Volume | {tech.get('volume', 0):,.0f} |\n"
        md += f"| 20D Avg Volume | {tech.get('avg_volume_20', 0):,.0f} |\n"
        vol_ratio = tech.get('volume', 0) / tech.get('avg_volume_20', 1) if tech.get('avg_volume_20', 0) > 0 else 0
        md += f"| Volume Ratio (vs 20D Avg) | {vol_ratio:.2f}x |\n"
        md += f"| Delivery % | {_safe(tech.get('delivery_pct'))}% |\n"
        md += f"| 20D Avg Delivery % | {_safe(tech.get('avg_delivery_pct_20'))}% |\n"
    else:
        md += "No technical data available.\n"
    md += "\n"

    # ── Option Chain ──
    md += "## Option Chain\n"
    if isinstance(chain, dict):
        md += f"| | |\n|---|---|\n"
        md += f"| **Spot Price** | {_safe(chain['underlying'])} |\n"
        md += f"| **Expiry** | {chain['expiry']} |\n"
        md += f"| **Days to Expiry** | {chain['days_to_expiry']} |\n"
        md += f"| **Lot Size** | {chain['lot_size']} |\n"
        md += f"| **ATM Strike** | {_safe(chain.get('atm_strike'))} |\n\n"

        # Grouped option chain: CE on left, Strike in middle, PE on right
        # This is the standard trader-friendly format
        md += "### Chain Data (CE | Strike | PE)\n"
        md += "| CE_IV | CE_Delta | CE_Theta | CE_Vega | CE_OI | CE_Vol | CE_Price | **Strike** | PE_Price | PE_Vol | PE_OI | PE_Vega | PE_Theta | PE_Delta | PE_IV |\n"
        md += "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"

        for row in chain['chain']:
            strike = row['strike']
            ce = row.get('ce', {})
            pe = row.get('pe', {})

            # Mark ATM strike
            strike_label = f"**{strike:.1f}**" if chain.get('atm_strike') and abs(strike - chain['atm_strike']) < 0.01 else f"{strike:.1f}"

            md += (
                f"| {_safe(ce.get('iv'))} "
                f"| {_safe(ce.get('delta'), '.4f')} "
                f"| {_safe(ce.get('theta'))} "
                f"| {_safe(ce.get('vega'))} "
                f"| {ce.get('oi', 0):,} "
                f"| {ce.get('volume', 0):,} "
                f"| {_safe(ce.get('price'))} "
                f"| {strike_label} "
                f"| {_safe(pe.get('price'))} "
                f"| {pe.get('volume', 0):,} "
                f"| {pe.get('oi', 0):,} "
                f"| {_safe(pe.get('vega'))} "
                f"| {_safe(pe.get('theta'))} "
                f"| {_safe(pe.get('delta'), '.4f')} "
                f"| {_safe(pe.get('iv'))} |\n"
            )

        # PCR summary
        total_ce_oi = sum(row.get('ce', {}).get('oi', 0) for row in chain['chain'])
        total_pe_oi = sum(row.get('pe', {}).get('oi', 0) for row in chain['chain'])
        pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0

        max_ce_oi_strike = max(chain['chain'], key=lambda r: r.get('ce', {}).get('oi', 0))['strike'] if chain['chain'] else 0
        max_pe_oi_strike = max(chain['chain'], key=lambda r: r.get('pe', {}).get('oi', 0))['strike'] if chain['chain'] else 0

        md += f"\n**OI Summary:**\n"
        md += f"- Put-Call Ratio (OI): {pcr:.2f}\n"
        md += f"- Max CE OI at Strike: {max_ce_oi_strike:.1f} (Resistance)\n"
        md += f"- Max PE OI at Strike: {max_pe_oi_strike:.1f} (Support)\n"
        md += f"- Total CE OI: {total_ce_oi:,} | Total PE OI: {total_pe_oi:,}\n"
    else:
        md += f"{chain}\n"
    md += "\n"

    # ── News ──
    md += "## Latest News & Sentiment\n"
    md += f"### {ticker} Specific News\n"
    md += f"{stock_news.get('text', 'No news.')}\n\n"

    md += "### Market Overview\n"
    md += f"{market_news.get('text', 'No news.')}\n"

    return md


if __name__ == "__main__":
    ticker = "RELIANCE"
    if len(sys.argv) > 1:
        ticker = sys.argv[1]

    content = generate_markdown(ticker)

    filename = f"context_{ticker}.md"
    with open(filename, "w") as f:
        f.write(content)

    print(f"\nContext saved to {filename}")
