# 🧠 One Lot AI

An AI-powered Indian F&O (Futures & Options) trading analysis platform. Enter a stock ticker and get live prices, technical analysis, option chains, and eventually AI-generated trade recommendations — all in one dashboard.

## Features

- **Live Prices** — Real-time LTP from Angel One SmartAPI
- **Technical Indicators** — RSI, MACD, Supertrend, Bollinger Bands
- **Price Charts** — Interactive candlestick charts with historical data
- **Option Chain** — Live CE/PE prices for nearest expiry with ATM detection
- **Ban Status** — F&O ban period tracking from NSE data
- **AI Trade Card** — (Coming Soon) LLM-powered trade suggestions

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite, Recharts, Lucide Icons |
| Backend | FastAPI, Uvicorn |
| Database | DuckDB (stocks & instruments) |
| Market Data | Angel One SmartAPI |
| Analysis | pandas, pandas_ta |

## Project Structure

```
one-lot-ai/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── database.py             # DuckDB connection
│   ├── api/
│   │   └── endpoints.py        # REST API routes
│   ├── services/
│   │   ├── angel_one.py        # Angel One API client
│   │   └── instrument_service.py # Scrip master management
│   ├── requirements.txt
│   └── .env                    # API credentials (not committed)
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Main dashboard
│   │   ├── components/
│   │   │   ├── StockChart.jsx
│   │   │   ├── TradeCard.jsx
│   │   │   └── OptionChain.jsx
│   │   ├── hooks/
│   │   │   └── useStockData.js
│   │   └── libs/
│   │       └── api.js
│   ├── package.json
│   └── vite.config.js
├── .gitignore
├── .env.example
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Angel One SmartAPI credentials ([get them here](https://smartapi.angelone.in/))

### 1. Clone & Setup Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Credentials

```bash
cp ../.env.example .env
# Edit .env with your Angel One API credentials
```

### 3. Start Backend

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

> **Note:** On first start, the backend downloads the Angel One instrument master (~50MB). This may take a moment.

### 4. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

### 5. Open the App

Visit `http://localhost:5173` and search for any F&O stock (e.g., `RELIANCE`, `TATASTEEL`, `HDFCBANK`).

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stock/{ticker}` | Stock info + live price + ban status |
| GET | `/api/stock/{ticker}/history?days=365` | Historical OHLCV data |
| GET | `/api/stock/{ticker}/technicals` | Technical indicators |
| GET | `/api/stock/{ticker}/chain` | Live option chain (nearest expiry) |

## Database

The app uses a DuckDB database (`stocks.duckdb`) located at `~/Development/price-vol-pattern/data/`. This database is populated by a separate data pipeline and contains:

- `fno_stocks` — F&O stock master list
- `daily_ohlcv` — Historical price data
- `fno_ban_period` — Ban period records

A separate in-memory DuckDB (`instruments.duckdb`) stores the Angel One instrument master for token lookups.

## Known Limitations

- Option chain prices are fetched serially (one API call per option). Performance can be improved with batch/concurrent fetching.
- DuckDB file locking means only one process can write to the database at a time. If the data pipeline is running, the backend may fail to connect.
- The AI trade recommendation is currently mocked — LLM integration is planned for Phase 3.

## License

Private project — not open source.
