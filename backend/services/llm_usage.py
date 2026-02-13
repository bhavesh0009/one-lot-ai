
import os
import logging
import duckdb
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
INSTRUMENT_DB_PATH = "instruments.duckdb"

# Approximate pricing per 1M tokens (USD) — update when pricing changes
# Source: Google AI pricing page
MODEL_PRICING = {
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60, "thinking": 0.70},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00, "thinking": 0.00},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40, "thinking": 0.00},
}


class LLMUsageTracker:
    def __init__(self):
        self.db_path = INSTRUMENT_DB_PATH
        self._ensure_table()

    def _ensure_table(self):
        try:
            conn = duckdb.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_usage (
                    id INTEGER DEFAULT nextval('llm_usage_seq'),
                    timestamp TIMESTAMP,
                    model VARCHAR,
                    caller VARCHAR,
                    ticker VARCHAR,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    thinking_tokens INTEGER,
                    total_tokens INTEGER,
                    cost_usd DOUBLE,
                    latency_ms INTEGER
                )
            """)
            conn.close()
        except duckdb.CatalogException:
            # Sequence doesn't exist, create it first
            conn = duckdb.connect(self.db_path)
            conn.execute("CREATE SEQUENCE IF NOT EXISTS llm_usage_seq START 1")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_usage (
                    id INTEGER DEFAULT nextval('llm_usage_seq'),
                    timestamp TIMESTAMP,
                    model VARCHAR,
                    caller VARCHAR,
                    ticker VARCHAR,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    thinking_tokens INTEGER,
                    total_tokens INTEGER,
                    cost_usd DOUBLE,
                    latency_ms INTEGER
                )
            """)
            conn.close()
        except Exception as e:
            logger.error(f"Failed to initialize llm_usage table: {e}")

    def _estimate_cost(self, model, input_tokens, output_tokens, thinking_tokens=0):
        pricing = MODEL_PRICING.get(model, MODEL_PRICING.get("gemini-2.5-flash"))
        cost = (
            (input_tokens / 1_000_000) * pricing["input"]
            + (output_tokens / 1_000_000) * pricing["output"]
            + (thinking_tokens / 1_000_000) * pricing.get("thinking", 0)
        )
        return round(cost, 6)

    def log_usage(self, model, caller, ticker, response, latency_ms=0):
        try:
            usage = getattr(response, 'usage_metadata', None)
            if not usage:
                return None

            input_tokens = getattr(usage, 'prompt_token_count', 0) or 0
            output_tokens = getattr(usage, 'candidates_token_count', 0) or 0
            thinking_tokens = getattr(usage, 'thoughts_token_count', 0) or 0
            total_tokens = getattr(usage, 'total_token_count', 0) or (input_tokens + output_tokens + thinking_tokens)

            cost_usd = self._estimate_cost(model, input_tokens, output_tokens, thinking_tokens)

            conn = duckdb.connect(self.db_path)
            conn.execute("""
                INSERT INTO llm_usage (timestamp, model, caller, ticker, input_tokens, output_tokens, thinking_tokens, total_tokens, cost_usd, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [datetime.now(), model, caller, ticker, input_tokens, output_tokens, thinking_tokens, total_tokens, cost_usd, latency_ms])
            conn.close()

            usage_info = {
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "thinking_tokens": thinking_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
            }
            logger.info(f"LLM usage [{caller}]: {input_tokens} in + {output_tokens} out = {total_tokens} total, ${cost_usd:.6f}")
            return usage_info

        except Exception as e:
            logger.error(f"Failed to log LLM usage: {e}")
            return None

    def get_usage_summary(self):
        try:
            conn = duckdb.connect(self.db_path, read_only=True)
            result = conn.execute("""
                SELECT
                    COUNT(*) as total_calls,
                    SUM(input_tokens) as total_input_tokens,
                    SUM(output_tokens) as total_output_tokens,
                    SUM(thinking_tokens) as total_thinking_tokens,
                    SUM(total_tokens) as total_tokens,
                    SUM(cost_usd) as total_cost_usd,
                    AVG(latency_ms) as avg_latency_ms
                FROM llm_usage
            """).fetchone()
            conn.close()

            if not result or result[0] == 0:
                return {"total_calls": 0, "total_cost_usd": 0}

            return {
                "total_calls": result[0],
                "total_input_tokens": result[1],
                "total_output_tokens": result[2],
                "total_thinking_tokens": result[3],
                "total_tokens": result[4],
                "total_cost_usd": round(result[5], 4),
                "avg_latency_ms": round(result[6]) if result[6] else 0,
            }
        except Exception as e:
            logger.error(f"Failed to get usage summary: {e}")
            return {"error": str(e)}

    def get_recent_usage(self, limit=20):
        try:
            conn = duckdb.connect(self.db_path, read_only=True)
            rows = conn.execute("""
                SELECT timestamp, model, caller, ticker, input_tokens, output_tokens, thinking_tokens, total_tokens, cost_usd, latency_ms
                FROM llm_usage
                ORDER BY timestamp DESC
                LIMIT ?
            """, [limit]).fetchall()
            conn.close()

            return [
                {
                    "timestamp": str(r[0]),
                    "model": r[1],
                    "caller": r[2],
                    "ticker": r[3],
                    "input_tokens": r[4],
                    "output_tokens": r[5],
                    "thinking_tokens": r[6],
                    "total_tokens": r[7],
                    "cost_usd": r[8],
                    "latency_ms": r[9],
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get recent usage: {e}")
            return []


# Singleton
llm_usage_tracker = LLMUsageTracker()
