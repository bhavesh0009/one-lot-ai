
import os
import logging
import duckdb
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
USAGE_DB_PATH = "llm_usage.duckdb"

# Pricing per 1M tokens (USD) — Source: Google AI pricing page
# For models with tiered pricing, using the ≤200k rate (our prompts are well under 200k)
MODEL_PRICING = {
    "gemini-3-pro-preview":     {"input": 2.00, "output": 12.00},
    "gemini-3-flash-preview":   {"input": 0.50, "output": 3.00},
    "gemini-2.5-pro":           {"input": 1.25, "output": 10.00},
    "gemini-2.5-flash":         {"input": 0.30, "output": 2.50},
    "gemini-2.5-flash-lite":    {"input": 0.10, "output": 0.40},
    "gemini-2.0-flash":         {"input": 0.10, "output": 0.40},
}

# Thinking tokens are billed at input rate for models that support thinking
THINKING_AT_INPUT_RATE = {"gemini-2.5-flash", "gemini-2.5-pro", "gemini-3-flash-preview", "gemini-3-pro-preview"}


class LLMUsageTracker:
    def __init__(self):
        self.conn = None
        self._initialize_db()

    def _initialize_db(self):
        try:
            self.conn = duckdb.connect(USAGE_DB_PATH)
            self.conn.execute("CREATE SEQUENCE IF NOT EXISTS llm_usage_seq START 1")
            self.conn.execute("""
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
        except Exception as e:
            logger.error(f"Failed to initialize llm_usage DB: {e}")

    def _get_pricing(self, model):
        """Look up pricing for a model, with fuzzy matching for versioned model names."""
        if model in MODEL_PRICING:
            return MODEL_PRICING[model]
        # Handle versioned names like "gemini-2.5-flash-preview-05-20"
        for key in MODEL_PRICING:
            if key in model or model.startswith(key):
                return MODEL_PRICING[key]
        logger.warning(f"No pricing found for model '{model}', defaulting to gemini-2.5-flash")
        return MODEL_PRICING["gemini-2.5-flash"]

    def _estimate_cost(self, model, input_tokens, output_tokens, thinking_tokens=0):
        pricing = self._get_pricing(model)
        # Thinking tokens billed at input rate for supported models
        thinking_rate = pricing["input"] if any(k in model for k in THINKING_AT_INPUT_RATE) else 0
        cost = (
            (input_tokens / 1_000_000) * pricing["input"]
            + (output_tokens / 1_000_000) * pricing["output"]
            + (thinking_tokens / 1_000_000) * thinking_rate
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

            self.conn.execute("""
                INSERT INTO llm_usage (timestamp, model, caller, ticker, input_tokens, output_tokens, thinking_tokens, total_tokens, cost_usd, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [datetime.now(), model, caller, ticker, input_tokens, output_tokens, thinking_tokens, total_tokens, cost_usd, latency_ms])

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
            result = self.conn.execute("""
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
            rows = self.conn.execute("""
                SELECT timestamp, model, caller, ticker, input_tokens, output_tokens, thinking_tokens, total_tokens, cost_usd, latency_ms
                FROM llm_usage
                ORDER BY timestamp DESC
                LIMIT ?
            """, [limit]).fetchall()

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
