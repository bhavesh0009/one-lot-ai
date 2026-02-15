# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

One Lot AI is a full-stack Indian F&O (Futures & Options) trading analysis platform that provides live prices, technical analysis, option chains, and news using Angel One SmartAPI and Gemini. The app is structured as a React frontend with a FastAPI backend, using DuckDB for historical data storage. It includes an AI-powered intraday trade recommendation engine using Gemini LLM.

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

**Three DuckDB databases:**
1. **stocks.duckdb** (read-only, shared): Located at `~/Development/price-vol-pattern/data/stocks.duckdb`. Contains historical OHLCV data, F&O stock master, and ban period records. Populated by a separate data pipeline. Connection in `backend/database.py` is read-only to prevent conflicts.

2. **instruments.duckdb** (app-managed): Created at backend root on first startup. Downloads Angel One instrument master (~50MB JSON) and stores it for token lookups. Managed by `instrument_service.py`.

3. **llm_usage.duckdb** (app-managed): Created at backend root on first LLM call. Stores token usage, cost, and latency for every Gemini API call. Managed by `llm_usage.py`. Kept separate from instruments.duckdb to avoid DuckDB connection conflicts.

**Key constraint:** DuckDB file locking means only one process can write. If the external data pipeline is running, the backend may fail to connect to stocks.duckdb.

### Backend Services (Singleton Pattern)

Services in `backend/services/` are initialized as singletons on startup:

- **angel_one.py**: Angel One SmartAPI client. Handles authentication using TOTP, fetches live LTP and market data. Session-based with JWT tokens.
  - **Rate limiting:** `/market/v1/quote` endpoint has rate limits (~20-25 concurrent requests). `get_market_data_batch()` implements intelligent batching:
    - Splits tokens into **5-token batches** (reduces quota consumption per request)
    - Adds **300ms delay between batches** to respect rate limits
    - Implements **exponential backoff retry** for AB1004 errors (1s → 2s → 4s delays)
    - Up to **3 retry attempts per batch**
    - Returns **partial results** even if some batches fail
    - Logs detailed batch progress for debugging

- **instrument_service.py**: Manages Angel One instrument master. Provides token lookups for NSE stocks and option chain symbol resolution. Downloads and caches data in instruments.duckdb.

- **greeks.py**: Local Black-Scholes calculator for option Greeks (delta, gamma, theta, vega, IV). No external API calls—computed in-process for performance.

- **news_service.py**: Fetches market and stock-specific news using Gemini Grounded Search API. Model name read from `GEMINI_MODEL_GROUNDING` env var. Tracks token usage via `llm_usage.py`.

- **trade_advisor.py**: AI-powered intraday trade recommendation engine. `build_context(ticker)` gathers all data (technicals, live price, option chain with Greeks, news) and formats as rich markdown. `analyze(ticker)` sends this context to Gemini with a trader persona system prompt and parses the structured JSON recommendation. Model name read from `GEMINI_MODEL` env var. Logs every recommendation to `llm_usage.duckdb` for forward testing.

- **llm_usage.py**: Tracks token usage (input, output, thinking), estimated cost (USD), and latency for every Gemini API call. Also logs full trade recommendations for forward testing. Stores in `llm_usage.duckdb`. Includes pricing table for all current Gemini models with fuzzy model name matching. Exports `GEMINI_MODEL` and `GEMINI_MODEL_GROUNDING` config for other services.

### API Endpoints (`backend/api/endpoints.py`)

All routes prefixed with `/api`:

- `GET /search?q={query}` — Fuzzy search F&O stocks by symbol/name
- `GET /stock/{ticker}` — Basic info + live LTP + ban status
- `GET /stock/{ticker}/history?days=365` — Historical OHLCV
- `GET /stock/{ticker}/technicals` — RSI, MACD, Supertrend, SMAs, delivery%, 52W high/low
- `GET /stock/{ticker}/chain` — Live option chain with Greeks (nearest expiry, ~16 strikes around ATM)
- `GET /stock/{ticker}/recommendation` — AI trade recommendation (Gemini LLM). Returns structured JSON with direction, strategy, trades, confidence, rationale, and token usage
- `GET /news/market` — General market news
- `GET /stock/{ticker}/news` — Stock-specific news
- `GET /recommendations?limit=50` — All past AI recommendations (for forward testing)
- `GET /stock/{ticker}/recommendations?limit=50` — Past recommendations for a specific stock
- `GET /llm/usage` — Aggregate LLM usage summary (total calls, tokens, cost)
- `GET /llm/usage/recent?limit=20` — Recent LLM usage records

**Option chain performance:** Uses batch API call via `get_market_data_batch()` to fetch all option prices + OI + volume in one request. Greeks computed locally.

### Trade Advisor Flow

1. `build_context(ticker)` gathers: live price (Angel One), full technicals (DB + pandas_ta), option chain with Greeks (Angel One batch + Black-Scholes), stock & market news (Gemini Grounded Search)
2. Formats everything as structured markdown (tables, bullet points)
3. Sends to Gemini with `system_instruction` (trader persona) + `contents` (dynamic markdown context)
4. Parses structured JSON response with: direction, strategy, trade legs, entry/SL/target, risk/reward, confidence score, rationale
5. Logs token usage + cost to `llm_usage.duckdb`
6. Logs full recommendation to `recommendations` table for forward testing

### Frontend Architecture

**Routing:** App uses React Router v6 for client-side routing:
- `frontend/src/App.jsx` — Route wrapper with Header + Routes component
- `frontend/src/main.jsx` — Wrapped with `<BrowserRouter>`
- `frontend/src/components/Header.jsx` — Navigation header with active link styling

**Pages:**
1. **DashboardPage** (`frontend/src/pages/DashboardPage.jsx`) — Main stock analysis dashboard
   - Ticker search via `TickerSearch.jsx`
   - Stock info, technicals, AI recommendation, chart, option chain, news
   - All logic extracted from original App.jsx

2. **RecommendationsPage** (`frontend/src/pages/RecommendationsPage.jsx`) — Historical recommendations table
   - Displays all past AI trade recommendations from `/api/recommendations`
   - Filters: by ticker (dropdown), direction (BULLISH/BEARISH/NEUTRAL buttons)
   - Sorting: by date, confidence, risk:reward ratio
   - Expandable rows: click to view full details (trade legs, rationale, risks, model info)
   - Color-coded by direction (green/red/gray)
   - Responsive table with horizontal scroll on mobile

**Data flow:**
1. User navigates to `/` → DashboardPage
2. User searches ticker → `TickerSearch.jsx` calls `/api/search`
3. User selects stock → `useStockData` hook orchestrates API calls
4. User navigates to `/recommendations` → RecommendationsPage
5. Page fetches `/api/recommendations?limit=100` → filter/sort client-side

**Key components:**
- `TickerSearch.jsx` — Autocomplete search with debouncing
- `Header.jsx` — Navigation with active state based on `useLocation()`
- `StockChart.jsx` — Recharts candlestick chart
- `OptionChain.jsx` — Greeks-enabled option chain table
- `TradeCard.jsx` — AI trade recommendation display (loads in background)
- `NewsCard.jsx` — Market/stock news display

**Custom hook:** `useStockData.js` manages data fetching, loading states, and logs. Centralized API orchestration.

**API Functions** (`frontend/src/libs/api.js`):
- `fetchRecommendations(limit=100)` — Fetch all past AI recommendations

### Live Data Strategy

For stock price:
1. **First attempt:** Angel One live LTP via SmartAPI
2. **Fallback:** Latest DB record if API fails
3. **Change calculation:** Live price compared against previous DB close

For option chain:
- Always live via Angel One (no fallback)
- Greeks computed locally using Black-Scholes model

## Configuration

### Environment Variables (`backend/.env`)
- `ANGEL_ONE_API_KEY`, `ANGEL_ONE_CLIENT_CODE`, `ANGEL_ONE_PASSWORD`, `ANGEL_ONE_TOTP_SECRET` — Angel One SmartAPI credentials
- `GEMINI_API_KEY` — Google Gemini API key
- `GEMINI_MODEL` — Gemini model for AI trade recommendations (default: `gemini-2.5-pro`). Used by `trade_advisor.py`.
- `GEMINI_MODEL_GROUNDING` — Gemini model for grounded search / news (default: `gemini-2.5-flash`). Must support Google Search tool. Used by `news_service.py`. Kept separate because not all models support grounding well (e.g. Pro lacks Google Search grounding).

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

### LLM Cost Tracking
Every Gemini API call (news + trade advisor) is logged to `llm_usage.duckdb` with input/output/thinking token counts and estimated USD cost. Pricing table in `llm_usage.py` covers all current Gemini models with fuzzy matching for versioned model names.

## Known Constraints

1. **Database locking:** If external data pipeline is running, backend cannot connect to stocks.duckdb (read-only prevents writes but connection can still fail).

2. **First startup delay:** Backend downloads 50MB Angel One instrument master on first run. Subsequent startups reuse cached data.

3. **TOTP-based auth:** Angel One requires TOTP secret for login. Session persists until backend restart.

4. **Indian market monthly expiry only:** Stock options on NSE only have monthly expiry. The trade advisor prompt reflects this.

5. **Angel One API rate limiting:** The `/market/v1/quote` endpoint (used for option chain prices) has rate limits that trigger AB1004 errors after ~20-25 concurrent requests. During market closed hours, the API may return persistent errors. Market hours: 9:15 AM - 3:30 PM IST (Mon-Fri). Retry logic with exponential backoff is implemented in `get_market_data_batch()` to handle this gracefully.

## Tech Debt

1. **`log_recommendation` / `get_recommendations` in wrong file:** These methods currently live in `llm_usage.py` but conceptually belong in `trade_advisor.py` (or a dedicated `recommendation_log.py`). `llm_usage.py` should only handle token/cost tracking. The `recommendations` table can stay in `llm_usage.duckdb` but the methods should be moved to the service that owns the domain.
