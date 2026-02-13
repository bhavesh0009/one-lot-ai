# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

One Lot AI is a full-stack Indian F&O (Futures & Options) trading analysis platform that provides live prices, technical analysis, option chains, and news using Angel One SmartAPI and Gemini. The app is structured as a React frontend with a FastAPI backend, using DuckDB for historical data storage.

## Development Commands

### Backend (FastAPI)
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

To run tests:
```bash
cd backend
source venv/bin/activate
pytest
```

### Frontend (React + Vite)
```bash
cd frontend
npm run dev      # Start dev server (localhost:5173)
npm run build    # Production build
npm run lint     # Run ESLint
```

### Environment Setup
Backend requires `.env` file with Angel One and Gemini API credentials. Copy from `backend/.env.example`.

## Architecture

### Data Layer

**Two DuckDB databases:**
1. **stocks.duckdb** (read-only, shared): Located at `~/Development/price-vol-pattern/data/stocks.duckdb`. Contains historical OHLCV data, F&O stock master, and ban period records. Populated by a separate data pipeline. Connection in `backend/database.py` is read-only to prevent conflicts.

2. **instruments.duckdb** (app-managed): Created at backend root on first startup. Downloads Angel One instrument master (~50MB JSON) and stores it for token lookups. Managed by `instrument_service.py`.

**Key constraint:** DuckDB file locking means only one process can write. If the external data pipeline is running, the backend may fail to connect to stocks.duckdb.

### Backend Services (Singleton Pattern)

Services in `backend/services/` are initialized as singletons on startup:

- **angel_one.py**: Angel One SmartAPI client. Handles authentication using TOTP, fetches live LTP and market data. Session-based with JWT tokens.

- **instrument_service.py**: Manages Angel One instrument master. Provides token lookups for NSE stocks and option chain symbol resolution. Downloads and caches data in instruments.duckdb.

- **greeks.py**: Local Black-Scholes calculator for option Greeks (delta, gamma, theta, vega, IV). No external API calls—computed in-process for performance.

- **news_service.py**: Fetches market and stock-specific news using Gemini Grounded Search API.

### API Endpoints (`backend/api/endpoints.py`)

All routes prefixed with `/api`:

- `GET /search?q={query}` — Fuzzy search F&O stocks by symbol/name
- `GET /stock/{ticker}` — Basic info + live LTP + ban status
- `GET /stock/{ticker}/history?days=365` — Historical OHLCV
- `GET /stock/{ticker}/technicals` — RSI, MACD, Supertrend, SMAs, delivery%, 52W high/low
- `GET /stock/{ticker}/chain` — Live option chain with Greeks (nearest expiry, ~16 strikes around ATM)
- `GET /news/market` — General market news
- `GET /stock/{ticker}/news` — Stock-specific news

**Option chain performance:** Uses batch API call via `get_market_data_batch()` to fetch all option prices + OI + volume in one request. Greeks computed locally.

### Frontend Architecture

**Main entry:** `frontend/src/App.jsx` — Dashboard with ticker search and data display.

**Data flow:**
1. User searches ticker → `TickerSearch.jsx` calls `/api/search`
2. User selects stock → `useStockData` hook orchestrates all API calls
3. Data loaded into local state → Passed to display components

**Key components:**
- `TickerSearch.jsx` — Autocomplete search with debouncing
- `StockChart.jsx` — Recharts candlestick chart
- `OptionChain.jsx` — Greeks-enabled option chain table
- `TradeCard.jsx` — Trade recommendation display (currently mocked)
- `NewsCard.jsx` — Market/stock news display

**Custom hook:** `useStockData.js` manages data fetching, loading states, and logs. Centralized API orchestration.

### Live Data Strategy

For stock price:
1. **First attempt:** Angel One live LTP via SmartAPI
2. **Fallback:** Latest DB record if API fails
3. **Change calculation:** Live price compared against previous DB close

For option chain:
- Always live via Angel One (no fallback)
- Greeks computed locally using Black-Scholes model

## Key Patterns

### Error Handling
- Backend: HTTPException with status codes (404, 500, 503)
- Frontend: Try-catch with console warnings for non-critical failures (option chain, news)
- Logging: Python logging to backend logs, console.warn in frontend

### CORS Configuration
Backend allows frontend ports 5173 and 5174 (Vite dev/alternate). Update `main.py` if frontend port changes.

### State Management
Frontend uses React hooks (useState, useCallback). No global state library—data flows through props from App.jsx.

### Pandas_ta Integration
Technical indicators calculated in `/stock/{ticker}/technicals` endpoint using pandas_ta. DataFrame loaded from DB, indicators appended in-place, latest values extracted.

## Known Constraints

1. **Database locking:** If external data pipeline is running, backend cannot connect to stocks.duckdb (read-only prevents writes but connection can still fail).

2. **First startup delay:** Backend downloads 50MB Angel One instrument master on first run. Subsequent startups reuse cached data.

3. **TOTP-based auth:** Angel One requires TOTP secret for login. Session persists until backend restart.

4. **Mocked AI recommendations:** TradeCard displays hardcoded mock data. LLM integration is planned future work.
